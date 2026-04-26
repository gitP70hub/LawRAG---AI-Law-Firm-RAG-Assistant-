"""
Pydantic v2 schemas for request validation and response serialisation.

Schema naming convention
------------------------
<Model>Base      – shared fields (no id / timestamps)
<Model>Create    – request body for POST endpoints
<Model>Update    – request body for PATCH endpoints (all optional)
<Model>Response  – full object returned by GET / POST / PATCH
<Model>List      – paginated list wrapper
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from api.models.db_models import CaseStatus, MessageRole


# ─────────────────────────────────────────────────────────────────────────────
# Shared config
# ─────────────────────────────────────────────────────────────────────────────

class _OrmBase(BaseModel):
    """All response schemas inherit from this to enable ORM mode."""
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# Case schemas
# ─────────────────────────────────────────────────────────────────────────────

class CaseBase(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        examples=["Smith v. Jones – Breach of Contract"],
    )
    description: Optional[str] = Field(
        None,
        max_length=5000,
        examples=["Client alleges failure to deliver contracted software…"],
    )
    client_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        examples=["Acme Corporation"],
    )
    status: CaseStatus = Field(default=CaseStatus.OPEN)


class CaseCreate(CaseBase):
    """Body expected when POSTing a new case."""
    pass


class CaseUpdate(BaseModel):
    """All fields optional — PATCH semantics."""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    client_name: Optional[str] = Field(None, min_length=2, max_length=255)
    status: Optional[CaseStatus] = None


class CaseResponse(_OrmBase, CaseBase):
    id: str
    created_at: datetime
    timeline_data: Optional[List[Dict[str, Any]]] = None
    timeline_generated_at: Optional[datetime] = None


class CaseListResponse(BaseModel):
    total: int
    items: List[CaseResponse]


class CaseStatusUpdate(BaseModel):
    """Body for PUT /api/v1/cases/{case_id}/status."""
    status: CaseStatus


class TimelineEventSchema(BaseModel):
    """Mirrors TimelineEvent from case_timeline.py — used in API responses."""
    date: str
    date_precision: str = "exact"
    event_type: str
    description: str
    parties_involved: List[str] = []
    document_source: Dict[str, Any]
    legal_significance: str = ""
    icon: str = "ℹ️"


class TimelineResponse(BaseModel):
    """Response body for GET /api/v1/cases/{case_id}/timeline."""
    case_id: uuid.UUID
    total_events: int
    generated_at: Optional[datetime] = None
    cached: bool = False
    events: List[TimelineEventSchema]


# ─────────────────────────────────────────────────────────────────────────────
# Document schemas
# ─────────────────────────────────────────────────────────────────────────────

class DocumentBase(BaseModel):
    filename: str = Field(..., max_length=512, examples=["contract_draft_v2.pdf"])
    file_path: str = Field(..., max_length=1024)
    file_size: Optional[int] = Field(None, ge=0, description="Size in bytes")
    mime_type: Optional[str] = Field(None, max_length=128, examples=["application/pdf"])
    is_indexed: bool = False


class DocumentCreate(BaseModel):
    """
    Used internally after a file is saved to disk.
    The case_id is injected from the URL path parameter.
    """
    filename: str = Field(..., max_length=512)
    file_path: str = Field(..., max_length=1024)
    file_size: Optional[int] = Field(None, ge=0)
    mime_type: Optional[str] = Field(None, max_length=128)


class DocumentResponse(_OrmBase, DocumentBase):
    id: str
    case_id: str
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    total: int
    items: List[DocumentResponse]


# ─────────────────────────────────────────────────────────────────────────────
# ChatMessage schemas
# ─────────────────────────────────────────────────────────────────────────────

class SourceReference(BaseModel):
    """A single RAG source citation attached to an assistant message."""
    doc_id: str
    filename: Optional[str] = None
    page: Optional[int] = Field(None, ge=1)
    score: Optional[float] = Field(None, ge=0.0, le=1.0)
    excerpt: Optional[str] = Field(None, max_length=500)


class ChatMessageBase(BaseModel):
    role: MessageRole
    content: str = Field(..., min_length=1, max_length=32_000)
    sources: Optional[List[SourceReference]] = None


class ChatMessageCreate(BaseModel):
    """Body sent by the client to start / continue a conversation."""
    content: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        examples=["What are the key obligations in the Smith contract?"],
    )


class ChatMessageResponse(_OrmBase, ChatMessageBase):
    id: str
    case_id: str
    created_at: datetime

    # sources stored as raw JSON in DB; coerce to list[dict]
    sources: Optional[List[Dict[str, Any]]] = None


class ChatHistoryResponse(BaseModel):
    case_id: str
    total: int
    messages: List[ChatMessageResponse]


# ─────────────────────────────────────────────────────────────────────────────
# Generic helpers
# ─────────────────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """Generic success / info response."""
    message: str


class ErrorResponse(BaseModel):
    """Standard error payload."""
    detail: str
    code: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Chat request / response schemas (used by /api/v1/chat)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Literal  # noqa: E402 — keep imports co-located with use

# Valid prompt/role identifiers exposed to API callers
PromptType = Literal[
    "client",
    "lawyer",
    "clause_analysis",
    "precedent",
    "timeline",
    "summary",
]


class ChatRequest(BaseModel):
    """Body sent by the frontend to the POST /api/v1/chat endpoint."""
    case_id: str = Field(
        ...,
        description="UUID of the case whose ChromaDB collection to query.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="The user's question or instruction.",
        examples=["Summarise the key obligations in the service agreement."],
    )
    role: Literal["client", "lawyer"] = Field(
        default="client",
        description=(
            "Who is asking — drives the system prompt tone. "
            "'client' → plain language; 'lawyer' → technical legal analysis."
        ),
    )
    prompt_type: PromptType = Field(
        default="client",
        description=(
            "Which specialised prompt to use. Defaults to the role value. "
            "Options: client, lawyer, clause_analysis, precedent, timeline, summary."
        ),
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of document chunks to retrieve from ChromaDB.",
    )


class ChatResponse(BaseModel):
    """Response returned by POST /api/v1/chat."""
    message_id: str = Field(
        ..., description="UUID of the saved assistant ChatMessage record."
    )
    answer: str = Field(..., description="The LLM-generated answer.")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="RAG source citations [{doc_id, filename, page_num, score, excerpt}].",
    )
    prompt_type: str = Field(..., description="The prompt type used for this query.")
