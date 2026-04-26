"""
backend/modules/case_timeline.py
==================================
AI Case Timeline Generator — LexAI's unique flagship feature.

Overview
--------
Given a ``case_id``, this module:

1. Fetches ALL document chunks from the case's ChromaDB collection via
   ``retrieve_all()`` (no query-vector — we want the *entire* corpus).
2. Formats the corpus into a numbered context block (reading order).
3. Calls the HF Inference API with ``TIMELINE_JSON_PROMPT`` which forces
   the model to return a raw JSON array.
4. Parses the JSON with retry logic (up to ``MAX_PARSE_RETRIES`` attempts)
   and validates each event with the ``TimelineEvent`` Pydantic model.
5. Returns ``list[TimelineEvent]`` sorted by date ascending.

Caching
-------
The caller (``cases.py`` router) is responsible for persisting the result
into ``Case.timeline_data`` (JSONB) and ``Case.timeline_generated_at`` so
subsequent requests return the cached value without re-running the LLM.

Token budget
------------
LLMs have context limits. For very large cases we:
- Cap the context at ``MAX_CONTEXT_CHARS`` characters.
- Use the first ``MAX_CONTEXT_CHUNKS`` chunks (reading order → most
  chronologically relevant text appears first).
- Log a warning when truncation occurs.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEndpoint
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, field_validator
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import settings
from prompts.timeline_json_prompt import TIMELINE_JSON_PROMPT
from rag.retriever import retrieve_all

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

MAX_CONTEXT_CHUNKS = 300     # max chunks fed to the LLM per timeline run
MAX_CONTEXT_CHARS  = 80_000  # hard character ceiling for the context block
MAX_PARSE_RETRIES  = 3       # JSON-parse retry attempts before giving up

# Fixed extraction question injected into the prompt
EXTRACTION_QUERY = (
    "Extract ALL chronological events from the provided legal documents. "
    "Return a complete JSON array following the schema exactly."
)

# Valid event_type values (mirrors the prompt taxonomy)
VALID_EVENT_TYPES = frozenset({
    "contract", "payment", "notice", "fir",
    "arrest", "filing", "hearing", "order",
    "judgment", "appeal", "other",
})

VALID_DATE_PRECISION = frozenset({"exact", "month_year", "year_only"})

VALID_ICONS = frozenset({"⚖️", "📄", "⚠️", "💰", "ℹ️"})


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic model — TimelineEvent
# ─────────────────────────────────────────────────────────────────────────────

class DocumentSource(BaseModel):
    """Source reference for a single timeline event."""
    filename: str = Field(..., description="PDF filename")
    page_num: int = Field(default=0, ge=0, description="1-based page number")


class TimelineEvent(BaseModel):
    """
    A single chronological event extracted from a case's documents.

    All fields are required in the LLM response; defaults are only used
    when the model omits a non-critical field.
    """
    date: str = Field(
        ...,
        description="ISO-8601 date string, e.g. '2023-03-15'.",
        examples=["2023-03-15"],
    )
    date_precision: str = Field(
        default="exact",
        description="'exact' | 'month_year' | 'year_only'",
    )
    event_type: str = Field(
        ...,
        description="One of the predefined event type strings.",
    )
    description: str = Field(
        ...,
        min_length=5,
        description="Plain English description of the event.",
    )
    parties_involved: List[str] = Field(
        default_factory=list,
        description="Party names with roles, e.g. 'Ravi Kumar (Plaintiff)'.",
    )
    document_source: DocumentSource = Field(
        ...,
        description="Filename and page number of the source document.",
    )
    legal_significance: str = Field(
        default="",
        description="One-sentence explanation of legal importance.",
    )
    icon: str = Field(
        default="ℹ️",
        description="Emoji icon representing event type.",
    )

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Accept ISO-8601 dates; coerce common formats."""
        v = v.strip()
        # Already ISO-8601?
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            pass
        # Try DD/MM/YYYY or DD-MM-YYYY
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y"):
            try:
                return datetime.strptime(v, fmt).date().isoformat()
            except ValueError:
                continue
        # Couldn't parse — keep the raw string but log a warning
        logger.warning(f"TimelineEvent: unrecognised date format '{v}', keeping raw.")
        return v

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        v = v.lower().strip()
        return v if v in VALID_EVENT_TYPES else "other"

    @field_validator("date_precision")
    @classmethod
    def validate_precision(cls, v: str) -> str:
        v = v.lower().strip()
        return v if v in VALID_DATE_PRECISION else "exact"

    @field_validator("icon")
    @classmethod
    def validate_icon(cls, v: str) -> str:
        return v if v in VALID_ICONS else "ℹ️"


# ─────────────────────────────────────────────────────────────────────────────
# LLM singleton (reuses the same HF endpoint as pipeline.py)
# ─────────────────────────────────────────────────────────────────────────────

_llm: HuggingFaceEndpoint | None = None


def _get_llm() -> HuggingFaceEndpoint:
    global _llm
    if _llm is None:
        logger.info(
            f"Timeline: initialising LLM '{settings.LLM_MODEL_ID}' …"
        )
        _llm = HuggingFaceEndpoint(
            repo_id=settings.LLM_MODEL_ID,
            huggingfacehub_api_token=settings.HUGGINGFACE_API_TOKEN,
            task="text-generation",
            max_new_tokens=4096,    # timelines can be long
            do_sample=False,        # greedy decoding → more deterministic JSON
            temperature=0.01,
            repetition_penalty=1.05,
            return_full_text=False,
        )
        logger.success("Timeline LLM ready.")
    return _llm


# ─────────────────────────────────────────────────────────────────────────────
# Context builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Render chunks into a numbered reading-order context block.

    Applies ``MAX_CONTEXT_CHUNKS`` and ``MAX_CONTEXT_CHARS`` limits.
    """
    selected = chunks[:MAX_CONTEXT_CHUNKS]
    if len(selected) < len(chunks):
        logger.warning(
            f"Context truncated: {len(chunks)} chunks → {len(selected)} "
            f"(limit={MAX_CONTEXT_CHUNKS})."
        )

    lines: List[str] = []
    total_chars = 0

    for i, chunk in enumerate(selected, start=1):
        entry = (
            f"[{i}] SOURCE: {chunk['filename']} | PAGE: {chunk['page_num']}\n"
            f"---\n"
            f"{chunk['content']}\n"
        )
        if total_chars + len(entry) > MAX_CONTEXT_CHARS:
            logger.warning(
                f"Context character limit ({MAX_CONTEXT_CHARS}) reached at "
                f"chunk {i}. Remaining chunks omitted."
            )
            break
        lines.append(entry)
        total_chars += len(entry)

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# JSON extraction with retry logic
# ─────────────────────────────────────────────────────────────────────────────

class _JSONParseError(Exception):
    """Raised when the LLM response cannot be parsed as a JSON array."""


def _extract_json_array(raw_text: str) -> List[Any]:
    """
    Extract the first JSON array from *raw_text*.

    The LLM sometimes wraps output in prose or code fences despite instructions.
    We strip those aggressively before JSON-parsing.

    Strategy
    --------
    1. Remove markdown code fences (``` … ```).
    2. Find the first '[' and last ']' and extract that substring.
    3. Parse with ``json.loads``.
    4. Raise ``_JSONParseError`` if any step fails.
    """
    text = raw_text.strip()

    # Strip code fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*", "", text)

    # Find JSON array boundaries
    start = text.find("[")
    end   = text.rfind("]")

    if start == -1 or end == -1 or end <= start:
        raise _JSONParseError(
            f"No JSON array delimiters found in LLM response. "
            f"First 200 chars: {text[:200]!r}"
        )

    json_str = text[start : end + 1]

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise _JSONParseError(
            f"JSON decode error: {exc}. "
            f"Attempted to parse: {json_str[:300]!r}"
        ) from exc

    if not isinstance(parsed, list):
        raise _JSONParseError(
            f"Parsed JSON is not an array (got {type(parsed).__name__})."
        )

    return parsed


def _parse_and_validate(raw_text: str) -> List[TimelineEvent]:
    """
    Parse the LLM response and validate each item as a ``TimelineEvent``.

    Raises ``_JSONParseError`` if the array cannot be extracted.
    Silently skips individual events that fail Pydantic validation (with a
    warning log) so one bad event doesn't discard the entire timeline.
    """
    raw_list = _extract_json_array(raw_text)

    events: List[TimelineEvent] = []
    for i, item in enumerate(raw_list):
        if not isinstance(item, dict):
            logger.warning(f"Timeline item {i} is not a dict — skipping.")
            continue
        try:
            events.append(TimelineEvent(**item))
        except (ValidationError, TypeError) as exc:
            logger.warning(f"Timeline item {i} failed validation: {exc} — skipping.")

    return events


# ─────────────────────────────────────────────────────────────────────────────
# LangChain LCEL chain
# ─────────────────────────────────────────────────────────────────────────────

def _build_chain():
    """Return a simple LCEL chain: prompt | llm | str_parser."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", TIMELINE_JSON_PROMPT),
            ("human", "{question}"),
        ]
    )
    return (
        RunnablePassthrough()
        | prompt
        | _get_llm()
        | StrOutputParser()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Core function — generate_timeline
# ─────────────────────────────────────────────────────────────────────────────

async def generate_timeline(
    case_id: uuid.UUID,
) -> List[TimelineEvent]:
    """
    Generate a structured chronological timeline for a case.

    Pipeline
    --------
    1. Fetch ALL chunks from ChromaDB (via ``retrieve_all``).
    2. Build context block (reading order, character-capped).
    3. Call the LLM with ``TIMELINE_JSON_PROMPT``.
    4. Extract + validate JSON → ``list[TimelineEvent]``.
    5. Sort by date ascending.
    6. Return.

    Retry logic
    -----------
    Steps 3–4 are retried up to ``MAX_PARSE_RETRIES`` times with exponential
    back-off if the LLM returns malformed JSON. On final failure, an empty
    list is returned (the caller logs the error and can surface it to the UI).

    Parameters
    ----------
    case_id : uuid.UUID
        The case whose ChromaDB collection to process.

    Returns
    -------
    list[TimelineEvent]
        Validated, date-sorted events. Empty list if no events found or
        if the LLM fails to return parseable JSON.
    """
    logger.info(f"Timeline generation started for case {str(case_id)[:8]}…")

    # ── 1. Retrieve all chunks ────────────────────────────────────────────────
    chunks = retrieve_all(case_id)

    if not chunks:
        logger.warning(
            f"No chunks in ChromaDB for case {str(case_id)[:8]}. "
            "Upload documents before generating timeline."
        )
        return []

    logger.info(f"Retrieved {len(chunks)} chunks for timeline generation.")

    # ── 2. Build context block ────────────────────────────────────────────────
    context = _build_context(chunks)

    # ── 3 & 4. LLM call with parse-retry logic ────────────────────────────────
    chain  = _build_chain()
    events: List[TimelineEvent] = []

    for attempt in range(1, MAX_PARSE_RETRIES + 1):
        try:
            logger.info(f"Timeline LLM call — attempt {attempt}/{MAX_PARSE_RETRIES} …")
            raw_answer: str = await chain.ainvoke(
                {
                    "context":  context,
                    "question": EXTRACTION_QUERY,
                }
            )
            logger.debug(f"Raw LLM output (first 500 chars): {raw_answer[:500]!r}")

            events = _parse_and_validate(raw_answer)
            logger.success(
                f"Timeline parsed successfully — {len(events)} events "
                f"on attempt {attempt}."
            )
            break  # success — exit retry loop

        except _JSONParseError as exc:
            logger.warning(
                f"Timeline attempt {attempt} failed JSON parse: {exc}"
            )
            if attempt == MAX_PARSE_RETRIES:
                logger.error(
                    f"All {MAX_PARSE_RETRIES} timeline attempts exhausted. "
                    f"Returning empty timeline for case {str(case_id)[:8]}."
                )
                return []

        except Exception as exc:
            logger.error(
                f"Unexpected error on timeline attempt {attempt}: {exc}",
                exc_info=True,
            )
            if attempt == MAX_PARSE_RETRIES:
                return []

    # ── 5. Sort by date ───────────────────────────────────────────────────────
    def _sort_key(ev: TimelineEvent) -> str:
        """Use the date string as sort key (ISO format sorts lexicographically)."""
        return ev.date or "0000-01-01"

    events.sort(key=_sort_key)

    logger.success(
        f"Timeline complete: {len(events)} events for case "
        f"{str(case_id)[:8]}…"
    )
    return events


# ─────────────────────────────────────────────────────────────────────────────
# Serialisation helpers
# ─────────────────────────────────────────────────────────────────────────────

def timeline_to_json(events: List[TimelineEvent]) -> List[Dict[str, Any]]:
    """Convert a list of TimelineEvents to plain dicts for JSONB storage."""
    return [e.model_dump() for e in events]


def timeline_from_json(data: List[Dict[str, Any]]) -> List[TimelineEvent]:
    """Reconstruct TimelineEvent objects from JSONB-stored dicts."""
    events: List[TimelineEvent] = []
    for item in data:
        try:
            events.append(TimelineEvent(**item))
        except (ValidationError, TypeError) as exc:
            logger.warning(f"Skipping invalid cached timeline event: {exc}")
    return events
