"""
backend/api/routes/upload.py
============================
Document upload endpoint for LawRAG.

Endpoint
--------
POST /api/v1/upload

Flow
----
1. Validate ``case_id`` exists in SQLite.
2. Validate file size and MIME type (PDF only in this version).
3. Check for duplicate (same case_id + filename) BEFORE inserting — avoids
   false-positive 409 errors from stale DB state.
4. Save file to ``uploads/{case_id}/original_filename``.
5. Insert a ``Document`` row with ``is_indexed=False`` and commit immediately
   so the record is visible even if ingestion fails.
6. Run the ingestion pipeline (PyMuPDF → splitter → embedder → ChromaDB).
7. Update ``Document.is_indexed = True`` in SQLite.
8. Return enriched response with chunk count.

Error handling
--------------
* 404 if the case doesn't exist.
* 400 if the file is not a PDF or exceeds the size limit.
* 409 if a file with the same name already exists for this case.
* 500 (with document record kept as is_indexed=False) if ingestion fails.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from api.models.db_models import Case, Document
from api.models.schemas import DocumentResponse
from core.config import settings
from database.connection import get_db
from rag.ingestion import ingest_pdf
from rag.retriever import add_documents

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/upload", tags=["Upload"])

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_MIME_TYPES = {"application/pdf"}


# ─────────────────────────────────────────────────────────────────────────────
# Enhanced response schema (includes chunk count)
# ─────────────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    """Extended upload response with RAG pipeline stats."""
    success: bool = True
    document_id: str
    filename: str
    chunks_created: int = 0
    message: str
    # Full document fields for UI update
    id: str
    case_id: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    is_indexed: bool = False

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _get_case_or_404(case_id: str, db: AsyncSession) -> Case:
    """Fetch a Case by PK or raise HTTP 404."""
    result = await db.execute(select(Case).where(Case.id == str(case_id)))
    case   = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found.",
        )
    return case


def _resolve_upload_dir(case_id: str) -> Path:
    """Return (and create) the per-case upload directory under UPLOAD_DIR."""
    upload_dir = Path(settings.UPLOAD_DIR) / str(case_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


async def _save_file(file: UploadFile, dest: Path) -> int:
    """
    Stream *file* to *dest* and return the total bytes written.
    Respects ``MAX_UPLOAD_SIZE_MB`` by aborting early if exceeded.
    """
    max_bytes = settings.max_upload_bytes
    written   = 0

    with dest.open("wb") as fh:
        while True:
            chunk = await file.read(1024 * 64)  # 64 KiB at a time
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                dest.unlink(missing_ok=True)    # clean up partial file
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"File exceeds the maximum allowed size of "
                        f"{settings.MAX_UPLOAD_SIZE_MB} MB."
                    ),
                )
            fh.write(chunk)

    return written


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF document and trigger RAG ingestion",
    responses={
        400: {"description": "Invalid file type or size"},
        404: {"description": "Case not found"},
        409: {"description": "Document already exists for this case"},
        500: {"description": "Ingestion pipeline failed"},
    },
)
async def upload_document(
    case_id: str = Form(
        ...,
        description="UUID of the case this document belongs to.",
        example="3fa85f64-5717-4562-b3fc-2c963f66afa6",
    ),
    file: UploadFile = File(
        ...,
        description="PDF file to upload (max 50 MB by default).",
    ),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """
    Upload a PDF to a case, ingest it into ChromaDB, and persist the
    ``Document`` record in SQLite.
    """

    # ── 1. Validate case exists ───────────────────────────────────────────────
    logger.info(f"Upload request | case={str(case_id)[:8]}… | file={file.filename!r}")
    await _get_case_or_404(case_id, db)

    # ── 2. Validate MIME type ─────────────────────────────────────────────────
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Only PDF files are accepted."
            ),
        )

    # ── 3. Determine destination path ─────────────────────────────────────────
    upload_dir = _resolve_upload_dir(case_id)
    safe_name  = Path(file.filename).name  # strip any path traversal
    dest_path  = upload_dir / safe_name

    logger.info(f"Upload destination: {dest_path}")

    # ── 4. BUG1 FIX: Explicit duplicate check by BOTH case_id AND filename ────
    # This prevents false-positive 409 errors. Same filename is only a duplicate
    # if it belongs to the SAME case. Different cases may share filenames.
    existing = await db.execute(
        select(Document).where(
            Document.filename == safe_name,
            Document.case_id  == str(case_id),   # ← scoped to THIS case only
        )
    )
    existing_doc = existing.scalar_one_or_none()
    if existing_doc is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A document named '{safe_name}' already exists for "
                f"case '{case_id}'."
            ),
        )

    # ── 5. Save file to disk ─────────────────────────────────────────────────
    logger.info(f"Saving '{safe_name}' → {dest_path}")
    file_size = await _save_file(file, dest_path)
    logger.success(f"Saved {file_size:,} bytes to '{dest_path}'.")

    # ── 6. Insert Document record with is_indexed=False and COMMIT immediately ─
    # Committing here ensures the document is visible in the documents list
    # even if the ingestion pipeline fails later.
    doc_id = str(uuid.uuid4())
    db_doc = Document(
        id        = doc_id,
        case_id   = str(case_id),
        filename  = safe_name,
        file_path = str(dest_path.resolve()),
        file_size = file_size,
        mime_type = file.content_type,
        is_indexed= False,
    )
    db.add(db_doc)
    await db.commit()           # ← COMMIT so document is visible immediately
    await db.refresh(db_doc)
    logger.info(f"Document record saved to DB: doc_id={str(doc_id)[:8]}… (is_indexed=False)")

    # ── 7. Run ingestion pipeline ─────────────────────────────────────────────
    chunks_created = 0
    try:
        logger.info(f"[STEP 1/4] Extracting text from PDF: {safe_name}")
        chunks = ingest_pdf(dest_path, doc_id, case_id)
        logger.info(f"[STEP 2/4] Chunking complete — {len(chunks)} chunks created")

        logger.info(f"[STEP 3/4] Embedding {len(chunks)} chunks with HuggingFace model …")
        added = add_documents(chunks, case_id)
        chunks_created = added
        logger.success(f"[STEP 4/4] Ingestion complete: {added} chunks stored in ChromaDB")
    except Exception as exc:
        # Document record already committed — leave is_indexed=False so user can see it
        logger.error(f"Ingestion failed for doc_id={str(doc_id)[:8]}…: {exc}", exc_info=True)
        return UploadResponse(
            success        = False,
            document_id    = doc_id,
            id             = doc_id,
            filename       = safe_name,
            case_id        = str(case_id),
            file_size      = file_size,
            mime_type      = file.content_type,
            is_indexed     = False,
            chunks_created = 0,
            message        = (
                f"Document saved but RAG indexing failed: {exc}. "
                "The document is visible but will not be searchable until re-indexed."
            ),
        )

    # ── 8. Mark document as indexed ───────────────────────────────────────────
    db_doc.is_indexed = True

    # Invalidate AI timeline cache — new document makes it stale
    case_result = await db.execute(select(Case).where(Case.id == str(case_id)))
    case_obj    = case_result.scalar_one_or_none()
    if case_obj and case_obj.timeline_data is not None:
        case_obj.timeline_data         = None
        case_obj.timeline_generated_at = None
        logger.info(
            f"Timeline cache invalidated for case {str(case_id)[:8]}… "
            "(new document uploaded)."
        )

    await db.commit()
    await db.refresh(db_doc)

    logger.success(
        f"✅ Document '{safe_name}' fully uploaded and indexed "
        f"(doc_id={str(doc_id)[:8]}…, {chunks_created} chunks)."
    )

    return UploadResponse(
        success        = True,
        document_id    = doc_id,
        id             = doc_id,
        filename       = safe_name,
        case_id        = str(case_id),
        file_size      = file_size,
        mime_type      = file.content_type,
        is_indexed     = True,
        chunks_created = chunks_created,
        message        = "Document uploaded and indexed successfully",
    )
