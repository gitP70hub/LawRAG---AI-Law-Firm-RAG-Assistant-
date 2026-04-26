"""
backend/api/routes/chat.py
==========================
Chat endpoints for LexAI — RAG-powered legal Q&A with conversation history.

Endpoints
---------
POST /api/v1/chat
    Send a message, trigger the RAG pipeline, persist both turns to
    PostgreSQL, and return the AI answer with source citations.

GET  /api/v1/chat/{case_id}
    Retrieve the full conversation history for a case, ordered oldest-first.

DELETE /api/v1/chat/{case_id}
    Wipe all ChatMessage rows for a case (fresh-start for a conversation).

Flow for POST /api/v1/chat
--------------------------
1. Validate case exists (404 if not).
2. Save user's ChatMessage (role=user) to PostgreSQL.
3. Resolve prompt_type — if caller sends role="lawyer" without specifying
   prompt_type, default to "lawyer" automatically.
4. Call run_rag_query(question, case_id, top_k, prompt_type).
5. Save assistant's ChatMessage (role=assistant) with sources JSON.
6. Return ChatResponse with message_id, answer, sources, prompt_type.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db_models import Case, ChatMessage, MessageRole
from api.models.schemas import (
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    MessageResponse,
)
from database.connection import get_db
from rag.pipeline import run_rag_query

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/chat")


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


def _resolve_prompt_type(role: str, prompt_type: str) -> str:
    """
    Derive the effective prompt type.

    Rules
    -----
    * If the caller explicitly passes a specialised prompt_type
      (clause_analysis, precedent, timeline, summary) — honour it.
    * Otherwise, fall back to the role value ("client" or "lawyer").

    This means:
      - role="client", prompt_type="client"   → CLIENT_PROMPT  ✓
      - role="lawyer", prompt_type="client"   → LAWYER_PROMPT  (role wins for defaults)
      - role="lawyer", prompt_type="summary"  → SUMMARY_PROMPT ✓
    """
    specialised = {"clause_analysis", "precedent", "timeline", "summary"}
    if prompt_type in specialised:
        return prompt_type
    # Default: mirror the role
    return role


async def _save_message(
    db: AsyncSession,
    case_id: str,
    role: MessageRole,
    content: str,
    sources: Optional[list] = None,
) -> ChatMessage:
    """Persist a ChatMessage row and return the flushed ORM instance."""
    msg = ChatMessage(
        id       = str(uuid.uuid4()),   # str for SQLite
        case_id  = case_id,
        role     = role,
        content  = content,
        sources  = sources,
    )
    db.add(msg)
    await db.flush()   # get DB-generated timestamps without committing yet
    return msg


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/chat  — send message & get AI answer
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message and get a RAG-powered legal answer",
    responses={
        404: {"description": "Case not found"},
        422: {"description": "Validation error"},
        503: {"description": "LLM / RAG pipeline unavailable"},
    },
)
async def send_message(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Send a user message, run the RAG pipeline against the case's ChromaDB
    collection, and return the AI-generated answer with source citations.

    Both the user message and the assistant reply are persisted to PostgreSQL
    so conversation history is maintained.
    """

    # ── 1. Validate case ──────────────────────────────────────────────────────
    await _get_case_or_404(body.case_id, db)

    # ── 2. Resolve effective prompt type ──────────────────────────────────────
    effective_prompt_type = _resolve_prompt_type(body.role, body.prompt_type)
    logger.info(
        f"Chat request | case={str(body.case_id)[:8]}… | role={body.role} | "
        f"prompt_type={effective_prompt_type} | msg={body.message[:60]!r}"
    )

    # ── 3. Persist user message ───────────────────────────────────────────────
    await _save_message(
        db      = db,
        case_id = body.case_id,
        role    = MessageRole.USER,
        content = body.message,
    )

    # ── 4. Run RAG pipeline ───────────────────────────────────────────────────
    logger.info(
        f"[RAG] Starting pipeline | case={str(body.case_id)[:8]}… | "
        f"top_k={body.top_k} | prompt={effective_prompt_type}"
    )
    try:
        rag_result = await run_rag_query(
            question     = body.message,
            case_id      = body.case_id,
            top_k        = body.top_k,
            prompt_type  = effective_prompt_type,
        )
    except Exception as exc:
        logger.error(f"RAG pipeline error: {exc}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"The AI pipeline encountered an error: {exc}",
        )

    answer  = rag_result["answer"]
    sources = rag_result["sources"]      # list[dict]

    # ── 5. Persist assistant message ──────────────────────────────────────────
    assistant_msg = await _save_message(
        db      = db,
        case_id = body.case_id,
        role    = MessageRole.ASSISTANT,
        content = answer,
        sources = sources,
    )
    await db.commit()
    await db.refresh(assistant_msg)

    logger.success(
        f"Chat complete | msg_id={str(assistant_msg.id)[:8]}… | "
        f"{len(sources)} sources cited."
    )

    # ── 6. Return response ────────────────────────────────────────────────────
    return ChatResponse(
        message_id   = assistant_msg.id,
        answer       = answer,
        sources      = sources,
        prompt_type  = effective_prompt_type,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/chat/{case_id}  — retrieve full conversation history
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{case_id}",
    response_model=ChatHistoryResponse,
    summary="Get conversation history for a case",
    responses={
        404: {"description": "Case not found"},
    },
)
async def get_chat_history(
    case_id: str,
    limit: int  = Query(default=50,  ge=1,  le=200, description="Max messages to return"),
    offset: int = Query(default=0,   ge=0,          description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryResponse:
    """
    Return the full conversation history for *case_id*, ordered oldest-first.

    Supports simple offset/limit pagination.
    """
    # Validate case
    await _get_case_or_404(case_id, db)

    # Total message count for the case
    count_result = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.case_id == case_id)
    )
    total: int = count_result.scalar_one()

    # Fetch paginated messages ordered by creation time
    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.case_id == case_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    messages: List[ChatMessage] = list(msg_result.scalars().all())

    return ChatHistoryResponse(
        case_id  = case_id,
        total    = total,
        messages = [ChatMessageResponse.model_validate(m) for m in messages],
    )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/v1/chat/{case_id}  — wipe conversation history
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{case_id}",
    response_model=MessageResponse,
    summary="Clear conversation history for a case",
    responses={
        404: {"description": "Case not found"},
    },
)
async def clear_chat_history(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Delete ALL ChatMessage rows for *case_id*.

    Useful when a user wants to start a fresh conversation without re-uploading
    documents (the ChromaDB collection is NOT affected).
    """
    await _get_case_or_404(case_id, db)

    result = await db.execute(
        delete(ChatMessage).where(ChatMessage.case_id == case_id)
    )
    await db.commit()

    deleted_count = result.rowcount
    logger.info(f"Cleared {deleted_count} messages for case {str(case_id)[:8]}…")

    return MessageResponse(
        message=f"Conversation history cleared ({deleted_count} messages deleted)."
    )
