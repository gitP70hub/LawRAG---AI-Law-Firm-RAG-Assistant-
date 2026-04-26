"""
Application-wide settings loaded from environment variables / .env file.
Uses pydantic-settings v2 for type-safe configuration.
"""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "LawRAG"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "CHANGE_ME"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://lexai:lexai_secret@localhost:5432/lexai_db"
    )
    SYNC_DATABASE_URL: str = (
        "postgresql+psycopg2://lexai:lexai_secret@localhost:5432/lexai_db"
    )

    # ── HuggingFace ───────────────────────────────────────────────────────────
    HUGGINGFACE_API_TOKEN: str = ""
    LLM_MODEL_ID: str = "mistralai/Mistral-7B-Instruct-v0.2"
    EMBEDDING_MODEL_ID: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_store"
    CHROMA_COLLECTION_NAME: str = "lexai_documents"

    # ── File Storage ──────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def cors_origins_list(self) -> List[str]:
        """Split comma-separated CORS origins into a list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()


settings: Settings = get_settings()
