"""
Async PostgreSQL connection setup using SQLAlchemy 2.x.

Exports
-------
engine      – AsyncEngine (shared across the application)
AsyncSessionLocal – async session factory
Base        – DeclarativeBase for ORM models
get_db      – FastAPI dependency that yields an AsyncSession
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from loguru import logger

from core.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

# SQLite does not support connection pooling options; detect and branch
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,          # log SQL statements in debug mode
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,           # verify connections before checkout
        pool_recycle=3600,            # recycle stale connections after 1 h
    )

# ─────────────────────────────────────────────────────────────────────────────
# Session factory
# ─────────────────────────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,       # keep attributes accessible after commit
    autocommit=False,
    autoflush=False,
)

# ─────────────────────────────────────────────────────────────────────────────
# Declarative base (shared by all ORM models)
# ─────────────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Common base for all SQLAlchemy ORM models."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI dependency
# ─────────────────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an :class:`AsyncSession` and guarantee it is closed after the
    request, even if an exception is raised.

    Usage::

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            logger.debug("DB session closed.")
