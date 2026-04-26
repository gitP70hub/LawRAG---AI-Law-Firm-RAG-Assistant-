"""
backend/api/routes/cases.py
============================
Full Cases CRUD + AI Timeline Generator endpoint.

Endpoints
---------
POST   /api/v1/cases                         – Create a new case
GET    /api/v1/cases                         – List all cases (paginated + filterable)
GET    /api/v1/cases/{case_id}               – Get case details
PUT    /api/v1/cases/{case_id}/status        – Update case status
GET    /api/v1/cases/{case_id}/timeline      – Get (or generate) AI timeline
DELETE /api/v1/cases/{case_id}/timeline      – Invalidate cached timeline
DELETE /api/v1/cases/{case_id}              – Soft-archive / hard-delete case

Timeline caching strategy
--------------------------
The first call to GET /timeline triggers the AI generation pipeline and
stores the result in ``Case.timeline_data`` (JSONB) + ``Case.timeline_generated_at``.
Subsequent calls return the cached data instantly.

Callers can pass ``?force_regenerate=true`` to bypass the cache.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db_models import Case, CaseStatus, Document
from api.models.schemas import (
    CaseCreate,
    CaseListResponse,
    CaseResponse,
    CaseStatusUpdate,
    CaseUpdate,
    MessageResponse,
    TimelineEventSchema,
    TimelineResponse,
)
from database.connection import get_db
from modules.case_timeline import (
    TimelineEvent,
    generate_timeline,
    timeline_from_json,
    timeline_to_json,
)

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/cases")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _get_case_or_404(case_id: str, db: AsyncSession) -> Case:
    """Fetch a case by its string ID, raise 404 if not found."""
    result = await db.execute(select(Case).where(Case.id == str(case_id)))
    case   = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found.",
        )
    return case


def _events_to_schema(events: List[TimelineEvent]) -> List[TimelineEventSchema]:
    """Convert domain model list to API schema list."""
    return [
        TimelineEventSchema(
            date               = ev.date,
            date_precision     = ev.date_precision,
            event_type         = ev.event_type,
            description        = ev.description,
            parties_involved   = ev.parties_involved,
            document_source    = ev.document_source.model_dump(),
            legal_significance = ev.legal_significance,
            icon               = ev.icon,
        )
        for ev in events
    ]


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/cases  — create case
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new case",
)
async def create_case(
    body: CaseCreate,
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Create and persist a new legal case record."""
    case = Case(
        id          = str(uuid.uuid4()),   # SQLite needs str, not UUID object
        title       = body.title,
        description = body.description,
        client_name = body.client_name,
        status      = body.status,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)

    logger.success(f"Case created: id={str(case.id)[:8]}… title={case.title!r}")
    return CaseResponse.model_validate(case)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/cases  — list cases
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=CaseListResponse,
    summary="List all cases",
)
async def list_cases(
    status_filter: Optional[CaseStatus] = Query(
        default=None,
        alias="status",
        description="Filter by case status.",
    ),
    client_name: Optional[str] = Query(
        default=None,
        description="Filter by client name (case-insensitive partial match).",
    ),
    limit: int  = Query(default=20, ge=1,  le=500),
    offset: int = Query(default=0,  ge=0),
    db: AsyncSession = Depends(get_db),
) -> CaseListResponse:
    """Return a paginated, filterable list of all cases."""
    query = select(Case)

    if status_filter is not None:
        query = query.where(Case.status == status_filter)

    if client_name:
        query = query.where(
            Case.client_name.ilike(f"%{client_name}%")
        )

    # Total count
    count_q  = select(func.count()).select_from(query.subquery())
    total    = (await db.execute(count_q)).scalar_one()

    # Paginated results
    result   = await db.execute(
        query.order_by(Case.created_at.desc()).offset(offset).limit(limit)
    )
    cases: List[Case] = list(result.scalars().all())

    return CaseListResponse(
        total = total,
        items = [CaseResponse.model_validate(c) for c in cases],
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/cases/{case_id}  — case details
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Get case details",
)
async def get_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Return full details for a single case."""
    case = await _get_case_or_404(case_id, db)
    return CaseResponse.model_validate(case)


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/cases/{case_id}  — update case fields
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Update case fields (PATCH semantics)",
)
async def update_case(
    case_id: str,
    body: CaseUpdate,
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Partially update a case — only supplied fields are changed."""
    case = await _get_case_or_404(case_id, db)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    await db.commit()
    await db.refresh(case)

    logger.info(f"Case {str(case_id)[:8]}… updated: {list(update_data.keys())}")
    return CaseResponse.model_validate(case)


# ─────────────────────────────────────────────────────────────────────────────
# PUT /api/v1/cases/{case_id}/status  — update status only
# ─────────────────────────────────────────────────────────────────────────────

@router.put(
    "/{case_id}/status",
    response_model=CaseResponse,
    summary="Update case status",
)
async def update_case_status(
    case_id: str,
    body: CaseStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """
    Update the workflow status of a case.

    Transitions
    -----------
    open → in_review → closed → archived
    Any transition is allowed by this endpoint; business-logic guards
    (if needed) should be added here in future.
    """
    case        = await _get_case_or_404(case_id, db)
    old_status  = case.status
    case.status = body.status

    await db.commit()
    await db.refresh(case)

    logger.info(
        f"Case {str(case_id)[:8]}… status: {old_status} → {body.status}"
    )
    return CaseResponse.model_validate(case)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/cases/{case_id}/timeline  — AI Timeline Generator
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{case_id}/timeline",
    response_model=TimelineResponse,
    summary="Generate or retrieve the AI case timeline",
    responses={
        202: {"description": "Timeline generation started (returned when generating)"},
        404: {"description": "Case not found"},
        503: {"description": "LLM / ChromaDB unavailable"},
    },
)
async def get_case_timeline(
    case_id: str,
    force_regenerate: bool = Query(
        default=False,
        description=(
            "Set to true to ignore the cache and re-run the AI generation "
            "pipeline. Useful after new documents are uploaded."
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    """
    Return a structured chronological timeline of events for the case.

    **First call (or force_regenerate=true)**:
    Fetches all document chunks from ChromaDB, runs the LLM extraction
    pipeline, validates the JSON, persists to PostgreSQL, and returns.
    Generation may take 30–90 seconds depending on document volume.

    **Subsequent calls**:
    Returns the cached ``timeline_data`` from PostgreSQL instantly.
    """
    case = await _get_case_or_404(case_id, db)

    # ── Cache hit ─────────────────────────────────────────────────────────────
    if case.timeline_data and not force_regenerate:
        logger.info(
            f"Timeline cache hit for case {str(case_id)[:8]}… "
            f"({len(case.timeline_data)} events, "
            f"generated {case.timeline_generated_at})."
        )
        events = timeline_from_json(case.timeline_data)
        return TimelineResponse(
            case_id      = case_id,
            total_events = len(events),
            generated_at = case.timeline_generated_at,
            cached       = True,
            events       = _events_to_schema(events),
        )

    # ── Cache miss — generate ─────────────────────────────────────────────────
    logger.info(
        f"Timeline cache miss for case {str(case_id)[:8]}… — "
        f"running generation pipeline."
    )

    try:
        events = await generate_timeline(case_id)
    except Exception as exc:
        logger.error(f"Timeline generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Timeline generation failed: {exc}",
        )

    # ── Persist to PostgreSQL ─────────────────────────────────────────────────
    now                        = datetime.now(tz=timezone.utc)
    case.timeline_data         = timeline_to_json(events)
    case.timeline_generated_at = now

    await db.commit()
    await db.refresh(case)

    logger.success(
        f"Timeline persisted for case {str(case_id)[:8]}…: "
        f"{len(events)} events."
    )

    return TimelineResponse(
        case_id      = case_id,
        total_events = len(events),
        generated_at = now,
        cached       = False,
        events       = _events_to_schema(events),
    )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/v1/cases/{case_id}/timeline  — invalidate timeline cache
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{case_id}/timeline",
    response_model=MessageResponse,
    summary="Invalidate the cached AI timeline",
)
async def invalidate_timeline(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Clear the cached timeline for a case.

    The next GET /timeline call will re-run the AI pipeline.
    Useful after uploading additional documents to a case.
    """
    case = await _get_case_or_404(case_id, db)
    case.timeline_data         = None
    case.timeline_generated_at = None
    await db.commit()

    logger.info(f"Timeline cache cleared for case {str(case_id)[:8]}…")
    return MessageResponse(message="Timeline cache invalidated. Next request will regenerate.")


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/v1/cases/{case_id}  — delete case
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{case_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a case and all associated data",
)
async def delete_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Permanently delete a case and cascade-delete all linked Documents and
    ChatMessages (enforced at the DB level via FK CASCADE).

    ⚠️ This does NOT delete the ChromaDB collection — use the admin CLI
    or a future /admin endpoint for that.
    """
    case = await _get_case_or_404(case_id, db)
    await db.delete(case)
    await db.commit()

    logger.warning(f"Case {str(case_id)[:8]}… permanently deleted.")
    return MessageResponse(
        message=f"Case '{case_id}' and all associated data have been deleted."
    )
