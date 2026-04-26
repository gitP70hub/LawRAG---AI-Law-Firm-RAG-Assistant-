"""
backend/api/routes/documents.py
================================
Documents endpoint for LawRAG.

Endpoints
---------
GET    /api/v1/documents/           – List documents for a case (filtered by case_id)
DELETE /api/v1/documents/{doc_id}   – Delete a document record + its ChromaDB vectors
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db_models import Document, Case
from api.models.schemas import DocumentListResponse, DocumentResponse, MessageResponse
from database.connection import get_db
from rag.retriever import delete_document as chroma_delete_document

router = APIRouter(prefix="/documents", tags=["Documents"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/documents/  — list documents for a case
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List all documents for a case",
    responses={
        404: {"description": "Case not found"},
    },
)
async def list_documents(
    case_id: str = Query(..., description="UUID of the case to list documents for"),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """
    Return all Document records belonging to *case_id*, ordered by upload time.
    Returns an empty list (not 404) if the case has no documents yet.
    """
    # Verify the case exists
    case_result = await db.execute(select(Case).where(Case.id == str(case_id)))
    case_obj = case_result.scalar_one_or_none()
    if case_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found.",
        )

    # Count total documents for this case
    count_result = await db.execute(
        select(func.count(Document.id)).where(Document.case_id == str(case_id))
    )
    total: int = count_result.scalar_one()

    # Fetch all documents for this case, ordered by upload date
    result = await db.execute(
        select(Document)
        .where(Document.case_id == str(case_id))
        .order_by(Document.uploaded_at.asc())
    )
    docs = list(result.scalars().all())

    logger.debug(
        f"GET /documents/?case_id={str(case_id)[:8]}… → {len(docs)} documents"
    )

    return DocumentListResponse(
        total=total,
        items=[DocumentResponse.model_validate(d) for d in docs],
    )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/v1/documents/{doc_id}  — delete a document
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{doc_id}",
    response_model=MessageResponse,
    summary="Delete a document and its vector index entries",
    responses={
        404: {"description": "Document not found"},
    },
)
async def delete_document_endpoint(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Delete a Document record from SQLite AND remove its chunks from ChromaDB.
    The physical file on disk is NOT removed (for audit trail purposes).
    """
    result = await db.execute(select(Document).where(Document.id == str(doc_id)))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found.",
        )

    case_id = doc.case_id
    filename = doc.filename

    # Remove from ChromaDB (best-effort — don't fail if already gone)
    try:
        removed = chroma_delete_document(doc_id, case_id)
        logger.info(
            f"Removed {removed} ChromaDB chunks for doc_id={str(doc_id)[:8]}…"
        )
    except Exception as exc:
        logger.warning(f"ChromaDB cleanup failed (non-fatal): {exc}")

    # Delete from SQLite
    await db.delete(doc)
    await db.commit()

    logger.success(
        f"Deleted document '{filename}' (doc_id={str(doc_id)[:8]}…) "
        f"from case {str(case_id)[:8]}…"
    )
    return MessageResponse(
        message=f"Document '{filename}' deleted successfully."
    )
