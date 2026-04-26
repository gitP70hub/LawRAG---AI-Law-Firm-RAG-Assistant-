"""
backend/api/routes/precedent.py
================================
Precedent Finder API endpoints.

Endpoints
---------
POST /api/v1/precedent   — Find Indian court precedents for a legal issue
GET  /api/v1/precedent/seed-status — Check ChromaDB seeding status
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from modules.precedent_finder import (
    Precedent,
    _get_precedent_collection,
    find_precedents,
    PRECEDENT_COLLECTION_NAME,
)

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/precedent")


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class PrecedentRequest(BaseModel):
    """Body for POST /api/v1/precedent."""

    legal_issue: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Natural-language description of the legal issue to research.",
        examples=[
            "My employer terminated my employment without a proper notice period "
            "and withheld my last month's salary. What are my rights under Indian law?"
        ],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of precedents to return.",
    )


class PrecedentItem(BaseModel):
    """Single precedent in the API response."""

    case_name: str
    court: str
    year: int
    citation: str
    summary: str
    key_ruling: str
    relevance_score: float
    relevance_reason: str


class PrecedentResponse(BaseModel):
    """Response body for POST /api/v1/precedent."""

    legal_issue: str
    total_found: int
    precedents: List[PrecedentItem]


class SeedStatusResponse(BaseModel):
    """Response for GET /api/v1/precedent/seed-status."""

    collection_name: str
    total_cases: int
    is_seeded: bool


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _to_item(p: Precedent) -> PrecedentItem:
    return PrecedentItem(
        case_name        = p.case_name,
        court            = p.court,
        year             = p.year,
        citation         = p.citation,
        summary          = p.summary,
        key_ruling       = p.key_ruling,
        relevance_score  = p.relevance_score,
        relevance_reason = p.relevance_reason,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/precedent — find precedents
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=PrecedentResponse,
    status_code=status.HTTP_200_OK,
    summary="Find Indian court precedents for a legal issue",
    responses={
        503: {"description": "LLM or ChromaDB unavailable"},
    },
)
async def search_precedents(body: PrecedentRequest) -> PrecedentResponse:
    """
    Perform a semantic search over the ``indian_case_laws`` ChromaDB collection
    and return the top-K most relevant Indian Supreme Court / High Court
    precedents for the given legal issue.

    The underlying pipeline:
    1. Embeds the ``legal_issue`` text with the shared LexAI embedder.
    2. Retrieves candidate cases from ChromaDB.
    3. Re-scores and enriches each case using the LLM.
    4. Returns validated, sorted results.
    """
    logger.info(
        f"POST /precedent — legal_issue={body.legal_issue[:80]!r} top_k={body.top_k}"
    )

    try:
        precedents = await find_precedents(
            query=body.legal_issue,
            top_k=body.top_k,
        )
    except Exception as exc:
        logger.error(f"Precedent search failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Precedent search failed: {exc}",
        )

    logger.success(f"Returning {len(precedents)} precedents.")
    return PrecedentResponse(
        legal_issue = body.legal_issue,
        total_found = len(precedents),
        precedents  = [_to_item(p) for p in precedents],
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/precedent/seed-status — collection health check
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/seed-status",
    response_model=SeedStatusResponse,
    summary="Check the status of the indian_case_laws ChromaDB collection",
)
async def seed_status() -> SeedStatusResponse:
    """
    Returns the total number of cases in the precedent collection and whether
    it has been seeded. Useful for diagnostics and health checks.
    """
    try:
        collection = _get_precedent_collection()
        count      = collection.count()
    except Exception as exc:
        logger.error(f"Seed status check failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ChromaDB unavailable: {exc}",
        )

    return SeedStatusResponse(
        collection_name = PRECEDENT_COLLECTION_NAME,
        total_cases     = count,
        is_seeded       = count > 0,
    )
