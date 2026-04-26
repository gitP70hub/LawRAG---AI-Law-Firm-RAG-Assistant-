"""
LawRAG – FastAPI application entry-point.

Responsibilities
----------------
* Bootstraps the FastAPI application instance.
* Configures CORS for the React dev-server.
* Mounts all API routers under /api/v1.
* Manages the async SQLAlchemy engine lifecycle (startup / shutdown).
* Exposes a health-check endpoint.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger

from core.config import settings
from database.connection import engine, Base

# ── Router imports ───────────────────────────────────────────────────────────
from api.routes import cases, documents, chat, health, upload, precedent, clause_analyze

# ─────────────────────────────────────────────────────────────────────────────
# Lifespan – startup / shutdown
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all DB tables on startup; dispose engine on shutdown."""
    logger.info("LawRAG starting up ...")

    async with engine.begin() as conn:
        # In production replace this with Alembic migrations.
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅  Database tables verified / created.")

    yield  # ── application runs here ──

    logger.info("LawRAG shutting down ...")
    await engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# Application factory
# ─────────────────────────────────────────────────────────────────────────────

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "LawRAG – AI-powered legal RAG assistant. "
            "Search case law, manage documents, and chat with an LLM grounded "
            "in your firm's knowledge base."
        ),
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    # NOTE: In Starlette/FastAPI, add_middleware() stacks in reverse — the LAST
    # call becomes the OUTERMOST wrapper.  CORSMiddleware must be outermost so
    # it can respond to OPTIONS preflight requests before GZip sees them.
    # Therefore: GZip first, CORS last.

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Build allowed origins list, always including the Vite dev server
    _cors_origins = list(settings.cors_origins_list)  # copy from settings
    for _dev in ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]:
        if _dev not in _cors_origins:
            _cors_origins.append(_dev)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    API_PREFIX = "/api/v1"

    app.include_router(health.router,          prefix=API_PREFIX, tags=["Health"])
    app.include_router(cases.router,           prefix=API_PREFIX, tags=["Cases"])
    app.include_router(documents.router,       prefix=API_PREFIX, tags=["Documents"])
    app.include_router(chat.router,            prefix=API_PREFIX, tags=["Chat"])
    app.include_router(upload.router,          prefix=API_PREFIX, tags=["Upload"])
    app.include_router(precedent.router,       prefix=API_PREFIX, tags=["Precedent Finder"])
    app.include_router(clause_analyze.router,  prefix=API_PREFIX, tags=["Clause Analyzer"])

    return app


app = create_application()
