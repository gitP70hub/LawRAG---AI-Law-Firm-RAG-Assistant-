"""
SQLAlchemy ORM models for LexAI.

Tables
------
cases         – Legal cases managed by the firm
documents     – Files uploaded and linked to a case
chat_messages – RAG conversation history per case
"""

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Use portable types — works with both PostgreSQL and SQLite
try:
    from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
    _JSONB = JSONB
    def _UUID_col(**kw):
        return mapped_column(PG_UUID(as_uuid=True), **kw)
except Exception:
    _JSONB = JSON
    def _UUID_col(**kw):
        return mapped_column(String(36), **kw)

from database.connection import Base


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class CaseStatus(str, enum.Enum):
    OPEN       = "open"
    IN_REVIEW  = "in_review"
    CLOSED     = "closed"
    ARCHIVED   = "archived"


class MessageRole(str, enum.Enum):
    USER      = "user"
    ASSISTANT = "assistant"
    SYSTEM    = "system"


# ─────────────────────────────────────────────────────────────────────────────
# Case
# ─────────────────────────────────────────────────────────────────────────────

class Case(Base):
    """
    Represents a legal case managed by the firm.

    Columns
    -------
    id                   : UUID primary key (auto-generated).
    title                : Short human-readable title of the case.
    description          : Full narrative / brief of the case.
    client_name          : Name of the client associated with this case.
    status               : Workflow status (open → in_review → closed / archived).
    created_at           : UTC timestamp set automatically on insert.
    timeline_data        : JSONB array of TimelineEvent dicts — cached result of
                           the AI Case Timeline Generator. NULL until first generated.
    timeline_generated_at: UTC timestamp of the last timeline generation run.
    """

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status_enum"),
        nullable=False,
        default=CaseStatus.OPEN,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # ── AI Timeline cache ────────────────────────────────────────────────────
    timeline_data: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="Cached list[TimelineEvent] JSON from the AI Timeline Generator.",
    )
    timeline_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp of last timeline generation.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    chat_messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} title={self.title!r} status={self.status}>"


# ─────────────────────────────────────────────────────────────────────────────
# Document
# ─────────────────────────────────────────────────────────────────────────────

class Document(Base):
    """
    A file (PDF, DOCX, TXT …) uploaded and associated with a :class:`Case`.

    Columns
    -------
    id          : UUID primary key.
    case_id     : FK → cases.id (cascade delete).
    filename    : Original filename as supplied by the user.
    file_path   : Absolute or relative path on the server filesystem.
    file_size   : Size in bytes (nullable until file is fully received).
    mime_type   : MIME type detected at upload time.
    is_indexed  : Whether the document has been vectorised into ChromaDB.
    uploaded_at : UTC timestamp set on insert.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_indexed: Mapped[bool] = mapped_column(default=False, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    case: Mapped["Case"] = relationship("Case", back_populates="documents")

    # ── Constraints ───────────────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("case_id", "filename", name="uq_document_case_filename"),
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} filename={self.filename!r} "
            f"case_id={self.case_id}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ChatMessage
# ─────────────────────────────────────────────────────────────────────────────

class ChatMessage(Base):
    """
    A single turn in a RAG conversation tied to a :class:`Case`.

    Columns
    -------
    id         : UUID primary key.
    case_id    : FK → cases.id (cascade delete).
    role       : Who authored the message (user / assistant / system).
    content    : Raw text of the message.
    sources    : JSON list of source document references used by the LLM.
                 Example: [{"doc_id": "...", "page": 3, "score": 0.87}]
    created_at : UTC timestamp set on insert.
    """

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role_enum"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="List of RAG source references [{doc_id, page, score}]",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    case: Mapped["Case"] = relationship("Case", back_populates="chat_messages")

    def __repr__(self) -> str:
        preview = self.content[:40].replace("\n", " ")
        return (
            f"<ChatMessage id={self.id} role={self.role} "
            f"case_id={self.case_id} content={preview!r}>"
        )
