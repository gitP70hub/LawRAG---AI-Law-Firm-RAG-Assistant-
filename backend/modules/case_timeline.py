"""
backend/modules/case_timeline.py
==================================
AI Case Timeline Generator.

Strategy
--------
1. Fetch ALL document chunks from ChromaDB.
2. Try a fast LLM call (30s timeout). If it returns valid JSON → use it.
3. If LLM is slow / unavailable / returns bad JSON → immediately fall back
   to the regex extractor which reliably finds year references, dates,
   and court terminology in document text.

This ensures the Timeline tab ALWAYS shows results quickly.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field, ValidationError, field_validator

from rag.retriever import retrieve_all

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────────────────

VALID_EVENT_TYPES = frozenset({
    "contract", "payment", "notice", "fir",
    "arrest", "filing", "hearing", "order",
    "judgment", "appeal", "other",
})
VALID_DATE_PRECISION = frozenset({"exact", "month_year", "year_only"})
VALID_ICONS = frozenset({"⚖️", "📄", "⚠️", "💰", "ℹ️"})


class DocumentSource(BaseModel):
    filename: str = Field(default="document")
    page_num: int = Field(default=0, ge=0)


class TimelineEvent(BaseModel):
    date: str = Field(...)
    date_precision: str = Field(default="exact")
    event_type: str = Field(default="other")
    description: str = Field(default="")
    parties_involved: List[str] = Field(default_factory=list)
    document_source: DocumentSource = Field(default_factory=DocumentSource)
    legal_significance: str = Field(default="")
    icon: str = Field(default="ℹ️")

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        v = v.strip()
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            pass
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y"):
            try:
                return datetime.strptime(v, fmt).date().isoformat()
            except ValueError:
                continue
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
# Regex-based timeline extractor (primary engine)
# ─────────────────────────────────────────────────────────────────────────────

def _regex_extract_timeline(chunks: List[Dict[str, Any]]) -> List[TimelineEvent]:
    """
    Extract timeline events from chunks using regex date patterns.

    Handles:
    - DD Month YYYY  → exact date
    - Month YYYY     → month_year precision
    - YYYY-MM-DD     → exact date
    - DD/MM/YYYY     → exact date
    - "In 1992, ..." → year_only (most common in legal documents)
    - "the 1997 case" → year_only
    """
    date_patterns: List[tuple] = [
        # Most specific first
        (r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|'
         r'September|October|November|December)\s+(\d{4})\b', 'exact'),
        (r'\b(January|February|March|April|May|June|July|August|'
         r'September|October|November|December)\s+(\d{4})\b', 'month_year'),
        (r'\b(\d{4})-(\d{2})-(\d{2})\b', 'exact'),
        (r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', 'exact'),
        # Indian law citation patterns: AIR 1997 SC, (1997), Act 2013
        (r'\bAIR\s+(\d{4})\b', 'year_only'),
        (r'\bAct[,\s]+(\d{4})\b', 'year_only'),
        (r'\bRules?[,\s]+(\d{4})\b', 'year_only'),
        (r'\b\((\d{4})\)', 'year_only'),           # (1997) citation form
        # Temporal prepositions before a year
        (r'(?:in|of|since|by|year|from|after|before|during|around|'
         r'between|until|till|circa|dated?|on)\s+(\d{4})\b', 'year_only'),
        # Year followed by comma + pronoun/article (strong sentence boundary)
        (r'(?<!\d)(\d{4}),\s+(?:she|he|the|it|this|that|they|there|a|an|her|his)', 'year_only'),
        # "the XXXX case/judgment/order/guidelines"
        (r'(?:the\s+)?(\d{4})\s+(?:case|judgment|judgment|order|guidelines?|act|ruling|verdict|decision)', 'year_only'),
    ]

    month_map = {
        'January': '01', 'February': '02', 'March': '03', 'April': '04',
        'May': '05', 'June': '06', 'July': '07', 'August': '08',
        'September': '09', 'October': '10', 'November': '11', 'December': '12',
    }

    seen_iso: set = set()
    events: List[TimelineEvent] = []

    for chunk in chunks:
        content  = chunk.get('content', '')
        filename = chunk.get('filename', 'document')
        page_num = int(chunk.get('page_num', 1))

        for pattern, precision in date_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                try:
                    g = match.groups()
                    iso: Optional[str] = None

                    if precision == 'exact' and len(g) == 3:
                        if g[1] and g[1].title() in month_map:   # DD Month YYYY
                            iso = f"{g[2]}-{month_map[g[1].title()]}-{int(g[0]):02d}"
                        elif g[0] and len(g[0]) == 4:            # YYYY-MM-DD
                            y, m, d = g
                            if m and d and 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                                iso = f"{y}-{m}-{d}"
                        else:                                      # DD/MM/YYYY
                            d_s, m_s, y_s = g
                            if d_s and m_s and y_s and 1 <= int(m_s) <= 12 and 1 <= int(d_s) <= 31:
                                iso = f"{y_s}-{int(m_s):02d}-{int(d_s):02d}"

                    elif precision == 'month_year' and len(g) == 2:
                        m_str = g[0].title() if g[0] else ''
                        y_str = g[1] if g[0] and g[0].title() in month_map else g[0]
                        m_str = g[0].title() if g[0] and g[0].title() in month_map else g[1].title()
                        if m_str in month_map and y_str and 1800 <= int(y_str) <= 2100:
                            iso = f"{y_str}-{month_map[m_str]}-01"

                    elif precision == 'year_only':
                        # Pick the group that is a valid year
                        year_str = next(
                            (x for x in g if x and x.isdigit() and 1800 <= int(x) <= 2100),
                            None
                        )
                        if year_str:
                            iso = f"{year_str}-01-01"

                    if not iso:
                        continue

                    # Skip duplicates (one event per unique date)
                    if iso in seen_iso:
                        continue
                    seen_iso.add(iso)

                    # Extract surrounding sentence for description
                    s = max(0, match.start() - 150)
                    e = min(len(content), match.end() + 300)
                    snippet = content[s:e].strip().replace('\n', ' ')

                    # Trim leading partial sentence
                    for sep in ['. ', '.\n', '\n\n', '; ']:
                        cut = snippet.find(sep)
                        if 0 < cut < 100:
                            snippet = snippet[cut + len(sep):]
                            break

                    desc = (snippet[:320] if snippet else f"Event on {iso}").strip()

                    # Classify event type from keywords
                    sl = desc.lower()
                    if any(w in sl for w in ['rape', 'assault', 'fir', 'harass', 'crime', 'murder', 'kidnap']):
                        etype, icon = 'fir', '⚠️'
                    elif any(w in sl for w in ['supreme court', 'high court', 'judgment', 'verdict', 'held', 'ruled', 'decided']):
                        etype, icon = 'judgment', '⚖️'
                    elif any(w in sl for w in ['petition', 'filed', 'writ', 'plaint', 'suit']):
                        etype, icon = 'filing', '⚖️'
                    elif any(w in sl for w in ['order', 'interim', 'stay', 'injunction', 'directed']):
                        etype, icon = 'order', '⚖️'
                    elif any(w in sl for w in ['hearing', 'bench', 'argued', 'counsel', 'argued before']):
                        etype, icon = 'hearing', '⚖️'
                    elif any(w in sl for w in ['appeal', 'challenged', 'impugned']):
                        etype, icon = 'appeal', '⚖️'
                    elif any(w in sl for w in ['arrested', 'bail', 'remand', 'custody', 'detained']):
                        etype, icon = 'arrest', '⚠️'
                    elif any(w in sl for w in ['contract', 'agreement', 'signed', 'deed', 'mou']):
                        etype, icon = 'contract', '📄'
                    elif any(w in sl for w in ['notice', 'letter', 'demand', 'served']):
                        etype, icon = 'notice', '📄'
                    elif any(w in sl for w in ['payment', 'paid', 'amount', 'rupee', 'money', 'dues']):
                        etype, icon = 'payment', '💰'
                    else:
                        etype, icon = 'other', 'ℹ️'

                    events.append(TimelineEvent(
                        date=iso,
                        date_precision=precision,
                        event_type=etype,
                        description=desc,
                        parties_involved=[],
                        document_source=DocumentSource(filename=filename, page_num=page_num),
                        legal_significance="Extracted from document text.",
                        icon=icon,
                    ))

                except Exception as exc:
                    logger.debug(f"Regex event parse error: {exc}")
                    continue

    # Sort chronologically
    events.sort(key=lambda ev: ev.date or "0000-01-01")
    logger.info(f"Regex extractor found {len(events)} events.")
    return events


# ─────────────────────────────────────────────────────────────────────────────
# Core public function
# ─────────────────────────────────────────────────────────────────────────────

async def generate_timeline(case_id: uuid.UUID) -> List[TimelineEvent]:
    """
    Generate a timeline for a case.

    Uses the regex extractor directly — fast, reliable, no LLM dependency.
    The HuggingFace free-tier LLM is too slow (30-120s per call) and
    returns inconsistent JSON. The regex approach is instant and handles
    all date formats found in Indian legal documents.
    """
    logger.info(f"Timeline generation started for case {str(case_id)[:8]}…")

    chunks = retrieve_all(case_id)

    if not chunks:
        logger.warning(
            f"No chunks in ChromaDB for case {str(case_id)[:8]}. "
            "Upload documents first."
        )
        return []

    logger.info(f"Retrieved {len(chunks)} chunks. Running regex extractor…")
    events = _regex_extract_timeline(chunks)

    logger.success(
        f"Timeline complete: {len(events)} events for case {str(case_id)[:8]}…"
    )
    return events


# ─────────────────────────────────────────────────────────────────────────────
# Serialisation helpers (used by cases.py route)
# ─────────────────────────────────────────────────────────────────────────────

def timeline_to_json(events: List[TimelineEvent]) -> List[Dict[str, Any]]:
    return [e.model_dump() for e in events]


def timeline_from_json(data: List[Dict[str, Any]]) -> List[TimelineEvent]:
    result: List[TimelineEvent] = []
    for item in data:
        try:
            result.append(TimelineEvent(**item))
        except (ValidationError, TypeError) as exc:
            logger.warning(f"Skipping invalid cached event: {exc}")
    return result
