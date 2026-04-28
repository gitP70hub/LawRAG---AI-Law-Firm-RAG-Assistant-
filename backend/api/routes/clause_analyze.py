"""
backend/api/routes/clause_analyze.py
======================================
Contract Clause Analyzer API endpoints.

Endpoints
---------
POST /api/v1/clause-analyze          — Analyse clauses in a case document
POST /api/v1/clause-analyze/raw-text — Analyse clauses in raw text (no DB lookup)
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db_models import Document
from database.connection import get_db
from modules.clause_analyzer import (
    ClauseAnalysis,
    ClauseResult,
    analyze_clauses,
    analyze_clauses_from_file,
)

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/clause-analyze")


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class ClauseAnalyzeRequest(BaseModel):
    """Body for POST /api/v1/clause-analyze (document lookup by case + name)."""

    case_id: uuid.UUID = Field(
        ...,
        description="UUID of the case owning the document.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    document_name: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Filename of the document to analyse (must match an uploaded file).",
        examples=["service_agreement_v2.pdf"],
    )


class RawTextAnalyzeRequest(BaseModel):
    """Body for POST /api/v1/clause-analyze/raw-text (direct text input)."""

    document_text: str = Field(
        ...,
        min_length=50,
        max_length=100_000,
        description="Full contract text to analyse.",
    )
    document_name: str = Field(
        default="contract",
        max_length=255,
        description="Optional display name for the document.",
    )


class ClauseResultSchema(BaseModel):
    """API-safe representation of a single ClauseResult."""

    clause_number: int
    clause_type: str
    clause_type_label: str
    clause_heading: str
    original_text: str
    plain_english: str
    risk_level: str
    risk_emoji: str
    risk_reason: str
    recommendation: str
    recommendation_note: str


class ClauseAnalysisResponse(BaseModel):
    """Response body for all clause-analyze endpoints."""

    document_name: str
    total_clauses: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    remove_count: int
    negotiate_count: int
    keep_count: int
    truncated: bool
    clauses: List[ClauseResultSchema]


# ─────────────────────────────────────────────────────────────────────────────
# Conversion helper
# ─────────────────────────────────────────────────────────────────────────────

def _analysis_to_response(analysis: ClauseAnalysis) -> ClauseAnalysisResponse:
    """Convert domain ClauseAnalysis to API response schema."""
    return ClauseAnalysisResponse(
        document_name     = analysis.document_name,
        total_clauses     = analysis.total_clauses,
        high_risk_count   = analysis.high_risk_count,
        medium_risk_count = analysis.medium_risk_count,
        low_risk_count    = analysis.low_risk_count,
        remove_count      = analysis.remove_count,
        negotiate_count   = analysis.negotiate_count,
        keep_count        = analysis.keep_count,
        truncated         = analysis.truncated,
        clauses=[
            ClauseResultSchema(
                clause_number      = c.clause_number,
                clause_type        = c.clause_type,
                clause_type_label  = c.clause_type_label,
                clause_heading     = c.clause_heading,
                original_text      = c.original_text,
                plain_english      = c.plain_english,
                risk_level         = c.risk_level,
                risk_emoji         = c.risk_emoji,
                risk_reason        = c.risk_reason,
                recommendation     = c.recommendation,
                recommendation_note= c.recommendation_note,
            )
            for c in analysis.clauses
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/clause-analyze — analyse a document linked to a case
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ClauseAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyse clauses in a document linked to a case",
    responses={
        404: {"description": "Case or document not found"},
        503: {"description": "LLM unavailable"},
    },
)
async def analyze_case_document(
    body: ClauseAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> ClauseAnalysisResponse:
    """
    Look up a document by ``case_id`` + ``document_name``, extract its text
    from disk, and run the full clause analysis pipeline.

    Steps
    -----
    1. Query the ``documents`` table for the matching record.
    2. Extract text from the file on disk (PDF or plain text).
    3. Run ``analyze_clauses_from_file``.
    4. Return a structured risk report.
    """
    logger.info(
        f"POST /clause-analyze — case_id={str(body.case_id)[:8]}… "
        f"document='{body.document_name}'"
    )

    # ── 1. Resolve document record ────────────────────────────────────────────
    result = await db.execute(
        select(Document).where(
            Document.case_id == str(body.case_id),   # cast UUID → str for SQLite
            Document.filename == body.document_name,
        )
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Document '{body.document_name}' not found in case "
                f"'{body.case_id}'. Ensure the file has been uploaded."
            ),
        )

    logger.info(
        f"Resolved document: id={str(doc.id)[:8]}… path='{doc.file_path}'"
    )

    # ── 2 & 3. Extract text + analyse ────────────────────────────────────────
    try:
        analysis = await analyze_clauses_from_file(
            file_path=doc.file_path,
            document_name=doc.filename,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Clause analysis failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Clause analysis failed: {exc}",
        )

    logger.success(
        f"Clause analysis complete for '{doc.filename}': "
        f"{analysis.total_clauses} clauses."
    )
    return _analysis_to_response(analysis)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/clause-analyze/raw-text — analyse raw text directly
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/raw-text",
    response_model=ClauseAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyse clauses in raw contract text (no document DB lookup)",
    responses={
        503: {"description": "LLM unavailable"},
    },
)
async def analyze_raw_text(body: RawTextAnalyzeRequest) -> ClauseAnalysisResponse:
    """
    Analyse clauses in raw contract text submitted directly in the request body.

    Use this endpoint when you want to analyse text that hasn't been uploaded
    as a file, or for quick prototyping / testing.
    """
    logger.info(
        f"POST /clause-analyze/raw-text — document='{body.document_name}' "
        f"({len(body.document_text):,} chars)"
    )

    try:
        analysis = await analyze_clauses(
            document_text=body.document_text,
            document_name=body.document_name,
        )
    except Exception as exc:
        logger.error(f"Raw-text clause analysis failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Clause analysis failed: {exc}",
        )

    logger.success(
        f"Raw-text analysis complete: {analysis.total_clauses} clauses."
    )
    return _analysis_to_response(analysis)
