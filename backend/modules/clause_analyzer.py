"""
backend/modules/clause_analyzer.py
=====================================
Contract Clause Analyzer — LexAI's contract risk assessment module.

Overview
--------
Given a case_id + document_name, this module:

1. Reads the document text from disk (the path is resolved via the
   ``Document`` DB record for the given case).
2. Extracts raw text using PyMuPDF (for PDFs) or plain read (for TXT/DOCX).
3. Sends the text to the LLM via ``CLAUSE_ANALYZER_SYSTEM_PROMPT`` which
   forces a raw JSON array response.
4. Parses and validates each element as a ``ClauseResult`` Pydantic model.
5. Builds and returns a ``ClauseAnalysis`` summary object.

Token budget
------------
Very large contracts are truncated at ``MAX_CONTRACT_CHARS`` before being
sent to the LLM, with a warning logged.

Token logging
-------------
All LLM calls log estimated input and output token counts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEndpoint
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, field_validator

from core.config import settings
from prompts.clause_analyzer_prompt import (
    CLAUSE_ANALYZER_HUMAN_PROMPT,
    CLAUSE_ANALYZER_SYSTEM_PROMPT,
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

MAX_CONTRACT_CHARS = 60_000   # char ceiling sent to LLM
MAX_PARSE_RETRIES  = 3

# Allowed clause types and their display-friendly labels
CLAUSE_TYPE_LABELS: Dict[str, str] = {
    "termination":    "Termination",
    "liability":      "Liability & Exclusions",
    "payment":        "Payment Terms",
    "arbitration":    "Arbitration / Dispute Resolution",
    "ip":             "Intellectual Property",
    "nda":            "Non-Disclosure Agreement",
    "indemnity":      "Indemnification",
    "force_majeure":  "Force Majeure",
    "governing_law":  "Governing Law & Jurisdiction",
    "warranty":       "Warranties & Representations",
    "confidentiality":"Confidentiality",
    "other":          "Other",
}

VALID_CLAUSE_TYPES  = frozenset(CLAUSE_TYPE_LABELS.keys())
VALID_RISK_LEVELS   = frozenset({"high", "medium", "low"})
VALID_RECOMMENDATIONS = frozenset({"keep", "negotiate", "remove"})


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────────────────

class ClauseResult(BaseModel):
    """Risk assessment for a single extracted contract clause."""

    clause_number: int = Field(
        ...,
        ge=1,
        description="Sequential clause number starting from 1.",
    )
    clause_type: str = Field(
        ...,
        description="Clause category (termination, liability, payment, etc.).",
    )
    clause_heading: str = Field(
        default="",
        description="Short heading for the clause.",
    )
    original_text: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Verbatim or closely paraphrased clause text.",
    )
    plain_english: str = Field(
        ...,
        min_length=10,
        description="Plain English explanation of the clause.",
    )
    risk_level: str = Field(
        ...,
        description="'high' | 'medium' | 'low'",
    )
    risk_reason: str = Field(
        default="",
        description="Explanation of the risk assessment.",
    )
    recommendation: str = Field(
        ...,
        description="'keep' | 'negotiate' | 'remove'",
    )
    recommendation_note: str = Field(
        default="",
        description="Brief justification for the recommendation.",
    )

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("clause_type")
    @classmethod
    def validate_clause_type(cls, v: str) -> str:
        v = v.lower().strip()
        return v if v in VALID_CLAUSE_TYPES else "other"

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        v = v.lower().strip()
        return v if v in VALID_RISK_LEVELS else "medium"

    @field_validator("recommendation")
    @classmethod
    def validate_recommendation(cls, v: str) -> str:
        v = v.lower().strip()
        return v if v in VALID_RECOMMENDATIONS else "negotiate"

    @field_validator("clause_number", mode="before")
    @classmethod
    def coerce_clause_number(cls, v: Any) -> int:
        try:
            return int(v)
        except (TypeError, ValueError):
            return 1

    @property
    def clause_type_label(self) -> str:
        return CLAUSE_TYPE_LABELS.get(self.clause_type, "Other")

    @property
    def risk_emoji(self) -> str:
        return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(self.risk_level, "⚪")


class ClauseAnalysis(BaseModel):
    """Aggregated result of a full contract clause analysis run."""

    document_name: str = Field(..., description="Name of the analysed document.")
    total_clauses: int = Field(..., ge=0, description="Total number of clauses extracted.")
    high_risk_count: int = Field(default=0, description="Clauses rated high risk.")
    medium_risk_count: int = Field(default=0, description="Clauses rated medium risk.")
    low_risk_count: int = Field(default=0, description="Clauses rated low risk.")
    remove_count: int = Field(default=0, description="Clauses recommended for removal.")
    negotiate_count: int = Field(default=0, description="Clauses recommended for negotiation.")
    keep_count: int = Field(default=0, description="Clauses recommended to keep.")
    clauses: List[ClauseResult] = Field(
        default_factory=list,
        description="Full list of analysed clauses.",
    )
    truncated: bool = Field(
        default=False,
        description="True if document text was truncated before LLM analysis.",
    )

    @classmethod
    def from_clauses(
        cls,
        document_name: str,
        clauses: List[ClauseResult],
        truncated: bool = False,
    ) -> "ClauseAnalysis":
        """Factory method: build ClauseAnalysis aggregates from a clause list."""
        return cls(
            document_name=document_name,
            total_clauses=len(clauses),
            high_risk_count=sum(1 for c in clauses if c.risk_level == "high"),
            medium_risk_count=sum(1 for c in clauses if c.risk_level == "medium"),
            low_risk_count=sum(1 for c in clauses if c.risk_level == "low"),
            remove_count=sum(1 for c in clauses if c.recommendation == "remove"),
            negotiate_count=sum(1 for c in clauses if c.recommendation == "negotiate"),
            keep_count=sum(1 for c in clauses if c.recommendation == "keep"),
            clauses=clauses,
            truncated=truncated,
        )


# ─────────────────────────────────────────────────────────────────────────────
# LLM singleton
# ─────────────────────────────────────────────────────────────────────────────

_llm: HuggingFaceEndpoint | None = None


def _get_llm() -> HuggingFaceEndpoint:
    global _llm
    if _llm is None:
        logger.info(
            f"ClauseAnalyzer: initialising LLM '{settings.LLM_MODEL_ID}' …"
        )
        _llm = HuggingFaceEndpoint(
            repo_id=settings.LLM_MODEL_ID,
            huggingfacehub_api_token=settings.HUGGINGFACE_API_TOKEN,
            task="text-generation",
            max_new_tokens=3072,
            do_sample=False,
            temperature=0.01,
            repetition_penalty=1.05,
            return_full_text=False,
        )
        logger.success("ClauseAnalyzer LLM ready.")
    return _llm


# ─────────────────────────────────────────────────────────────────────────────
# LangChain chain
# ─────────────────────────────────────────────────────────────────────────────

def _build_chain():
    """Return an LCEL chain: prompt | llm | str_parser."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CLAUSE_ANALYZER_SYSTEM_PROMPT),
            ("human",  CLAUSE_ANALYZER_HUMAN_PROMPT),
        ]
    )
    return RunnablePassthrough() | prompt | _get_llm() | StrOutputParser()


# ─────────────────────────────────────────────────────────────────────────────
# JSON parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

class _JSONParseError(Exception):
    """Raised when the LLM response cannot be parsed as a JSON array."""


def _extract_json_array(raw_text: str) -> List[Any]:
    """Strip prose/fences and extract the first JSON array from raw_text."""
    text = raw_text.strip()
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*", "", text)

    start = text.find("[")
    end   = text.rfind("]")

    if start == -1 or end == -1 or end <= start:
        raise _JSONParseError(
            f"No JSON array delimiters found. First 200 chars: {text[:200]!r}"
        )

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise _JSONParseError(f"JSON decode error: {exc}") from exc

    if not isinstance(parsed, list):
        raise _JSONParseError(
            f"Parsed JSON is not an array (got {type(parsed).__name__})."
        )

    return parsed


def _parse_clauses(raw_text: str) -> List[ClauseResult]:
    """Parse LLM output and validate each item as a ClauseResult."""
    raw_list = _extract_json_array(raw_text)
    clauses: List[ClauseResult] = []

    for i, item in enumerate(raw_list):
        if not isinstance(item, dict):
            logger.warning(f"Clause item {i} is not a dict — skipping.")
            continue
        try:
            clauses.append(ClauseResult(**item))
        except (ValidationError, TypeError) as exc:
            logger.warning(f"Clause item {i} validation failed: {exc} — skipping.")

    return clauses


# ─────────────────────────────────────────────────────────────────────────────
# Document text extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_text_from_file(file_path: str) -> str:
    """
    Extract raw text from a document file.

    Supports: PDF (via PyMuPDF), TXT, and other text-based formats.
    Falls back to UTF-8 plain-text read for non-PDF files.
    """
    p = Path(file_path)

    if not p.exists():
        raise FileNotFoundError(f"Document file not found: {file_path!r}")

    suffix = p.suffix.lower()

    if suffix == ".pdf":
        try:
            import fitz  # PyMuPDF
            text_parts: List[str] = []
            with fitz.open(str(p)) as doc:
                for page in doc:
                    text_parts.append(page.get_text("text"))
            return "\n".join(text_parts)
        except ImportError:
            logger.warning(
                "PyMuPDF (fitz) not installed. Falling back to plain text read."
            )
        except Exception as exc:
            logger.warning(f"PDF extraction failed: {exc}. Trying plain text.")

    # Fallback: plain UTF-8 read (works for TXT, DOCX-extracted text, etc.)
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(
            f"Cannot extract text from '{file_path}': {exc}"
        ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def analyze_clauses(
    document_text: str,
    document_name: str = "contract",
) -> ClauseAnalysis:
    """
    Analyse all clauses in *document_text* and return a structured risk report.

    Pipeline
    --------
    1. Truncate document text if it exceeds ``MAX_CONTRACT_CHARS``.
    2. Estimate token count and log it.
    3. Call the LLM (via LCEL chain) with ``CLAUSE_ANALYZER_SYSTEM_PROMPT``.
    4. Extract and validate the JSON array response.
    5. Retry up to ``MAX_PARSE_RETRIES`` times on parse failure.
    6. Build and return ``ClauseAnalysis`` with aggregated risk stats.

    Parameters
    ----------
    document_text : str
        Full text of the contract document.
    document_name : str
        Filename / label for the document (used in the response object).

    Returns
    -------
    ClauseAnalysis
        Validated analysis result. Returns a ClauseAnalysis with an empty
        clause list on complete failure.
    """
    logger.info(
        f"ClauseAnalyzer: starting analysis of '{document_name}' "
        f"({len(document_text):,} chars)."
    )

    # ── 1. Truncate if necessary ──────────────────────────────────────────────
    truncated = False
    if len(document_text) > MAX_CONTRACT_CHARS:
        logger.warning(
            f"Document '{document_name}' exceeds {MAX_CONTRACT_CHARS} chars "
            f"({len(document_text):,}). Truncating."
        )
        document_text = document_text[:MAX_CONTRACT_CHARS]
        truncated = True

    # ── 2. Log estimated token count ─────────────────────────────────────────
    approx_tokens = len(document_text) // 4
    logger.info(
        f"ClauseAnalyzer: estimated input tokens ≈ {approx_tokens:,} "
        f"(truncated={truncated})"
    )

    # ── 3 & 4. LLM call with retry ───────────────────────────────────────────
    chain  = _build_chain()
    clauses: List[ClauseResult] = []

    for attempt in range(1, MAX_PARSE_RETRIES + 1):
        try:
            logger.info(
                f"ClauseAnalyzer LLM call — attempt {attempt}/{MAX_PARSE_RETRIES} …"
            )
            raw_answer: str = await chain.ainvoke(
                {"contract_text": document_text}
            )

            output_tokens = len(raw_answer) // 4
            logger.info(
                f"ClauseAnalyzer LLM responded. "
                f"Output ≈ {output_tokens} tokens. "
                f"Total ≈ {approx_tokens + output_tokens} tokens."
            )
            logger.debug(
                f"Raw LLM output (first 400 chars): {raw_answer[:400]!r}"
            )

            clauses = _parse_clauses(raw_answer)
            logger.success(
                f"ClauseAnalyzer parsed {len(clauses)} clauses on attempt {attempt}."
            )
            break

        except _JSONParseError as exc:
            logger.warning(
                f"ClauseAnalyzer attempt {attempt} parse error: {exc}"
            )
            if attempt == MAX_PARSE_RETRIES:
                logger.error(
                    "All parse attempts exhausted — returning empty analysis."
                )
                return ClauseAnalysis.from_clauses(
                    document_name=document_name,
                    clauses=[],
                    truncated=truncated,
                )

        except Exception as exc:
            logger.error(
                f"Unexpected error on attempt {attempt}: {exc}", exc_info=True
            )
            if attempt == MAX_PARSE_RETRIES:
                return ClauseAnalysis.from_clauses(
                    document_name=document_name,
                    clauses=[],
                    truncated=truncated,
                )

    analysis = ClauseAnalysis.from_clauses(
        document_name=document_name,
        clauses=clauses,
        truncated=truncated,
    )

    logger.success(
        f"ClauseAnalyzer complete: {analysis.total_clauses} clauses | "
        f"🔴{analysis.high_risk_count} 🟡{analysis.medium_risk_count} "
        f"🟢{analysis.low_risk_count}"
    )
    return analysis


async def analyze_clauses_from_file(
    file_path: str,
    document_name: Optional[str] = None,
) -> ClauseAnalysis:
    """
    Convenience wrapper: extract text from a file, then call analyze_clauses.

    Parameters
    ----------
    file_path     : str
        Absolute or relative path to the contract document.
    document_name : str, optional
        Display name; defaults to the filename stem.

    Returns
    -------
    ClauseAnalysis
    """
    p = Path(file_path)
    name = document_name or p.name

    logger.info(f"ClauseAnalyzer: reading file '{file_path}' …")
    text = _extract_text_from_file(file_path)
    logger.info(f"Extracted {len(text):,} chars from '{name}'.")

    return await analyze_clauses(document_text=text, document_name=name)
