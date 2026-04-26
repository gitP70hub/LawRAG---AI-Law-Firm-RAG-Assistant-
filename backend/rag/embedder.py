"""
backend/rag/embedder.py
=======================
HuggingFace sentence-transformers embeddings wrapped as a LangChain
``Embeddings`` implementation.

Design decisions
----------------
* Uses ``sentence-transformers/all-MiniLM-L6-v2`` (384-dim, fast, good
  retrieval quality for legal text at this scale).
* The underlying SentenceTransformer model is loaded **once** and reused
  across all requests via a module-level singleton.
* Normalise embeddings (L2) so cosine similarity == dot product in ChromaDB.
* Batch size is configurable via ``EMBED_BATCH_SIZE`` to avoid OOM on CPU.

Dependencies: sentence-transformers, langchain-core
"""

from __future__ import annotations

from typing import List

from langchain_core.embeddings import Embeddings
from loguru import logger
from sentence_transformers import SentenceTransformer

from core.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

EMBED_BATCH_SIZE = 64       # documents per encoding batch
EMBED_DEVICE     = "cpu"    # change to "cuda" if GPU is available


# ─────────────────────────────────────────────────────────────────────────────
# Singleton model loader
# ─────────────────────────────────────────────────────────────────────────────

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """
    Load the SentenceTransformer model once and cache it for the process
    lifetime.  Thread-safe: FastAPI workers are async, not multi-threaded.
    """
    global _model
    if _model is None:
        model_id = settings.EMBEDDING_MODEL_ID
        logger.info(f"Loading embedding model '{model_id}' on {EMBED_DEVICE} …")
        _model = SentenceTransformer(model_id, device=EMBED_DEVICE)
        logger.success(f"Embedding model loaded — dim={_model.get_sentence_embedding_dimension()}")
    return _model


# ─────────────────────────────────────────────────────────────────────────────
# LangChain Embeddings wrapper
# ─────────────────────────────────────────────────────────────────────────────

class LawRAGEmbeddings(Embeddings):
    """
    LangChain-compatible embeddings class backed by a local
    ``sentence-transformers`` model.

    The class is intentionally stateless — it delegates to the module-level
    singleton so it can be instantiated freely without reloading weights.

    Example
    -------
    >>> embedder = LawRAGEmbeddings()
    >>> vectors  = embedder.embed_documents(["contract clause …", "…"])
    >>> query_v  = embedder.embed_query("What are the payment terms?")
    """

    # Pydantic-style config accepted by some LangChain internals
    class Config:
        arbitrary_types_allowed = True

    # ── LangChain interface ────────────────────────────────────────────────────

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of document strings.

        Parameters
        ----------
        texts : list[str]
            Raw text chunks (already cleaned by the ingestion pipeline).

        Returns
        -------
        list[list[float]]
            One float vector per input string, L2-normalised.
        """
        if not texts:
            return []

        model = _get_model()
        logger.debug(f"Embedding {len(texts)} documents in batches of {EMBED_BATCH_SIZE} …")

        vectors = model.encode(
            texts,
            batch_size=EMBED_BATCH_SIZE,
            normalize_embeddings=True,   # cosine sim == dot product in Chroma
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        # numpy → plain Python float lists (JSON-serialisable)
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query string.

        Parameters
        ----------
        text : str
            The user's natural-language question.

        Returns
        -------
        list[float]
            L2-normalised embedding vector.
        """
        model = _get_model()
        vector = model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vector.tolist()


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience instance
# ─────────────────────────────────────────────────────────────────────────────

def get_embedder() -> LawRAGEmbeddings:
    """Return a ready-to-use :class:`LawRAGEmbeddings` instance."""
    return LawRAGEmbeddings()
