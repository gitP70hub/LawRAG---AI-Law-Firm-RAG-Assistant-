"""
backend/rag/retriever.py
========================
ChromaDB vector-store interface for LexAI.

Design
------
* One ChromaDB **collection per case_id** — strict data isolation so a query
  for case A can never accidentally surface documents from case B.
* Collections are created lazily and persisted to disk under
  ``data/chroma_db/``.
* Uses :class:`~backend.rag.embedder.LexAIEmbeddings` for embedding queries
  at retrieval time (same model as ingestion — critical for correctness).
* Returns top-K chunks (default 5) as a list of dicts that match the
  ``SourceReference`` Pydantic schema expected by the API layer.
* Supports both **add** (upsert) and **delete** operations so documents can
  be re-ingested or removed.

Dependencies: chromadb, langchain-community
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document
from loguru import logger

from core.config import settings
from rag.embedder import get_embedder, LawRAGEmbeddings

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

TOP_K              = 5      # number of chunks to retrieve per query
SIMILARITY_THRESHOLD = 0.30  # discard chunks below this cosine similarity

# ChromaDB persist directory (resolved at import time)
CHROMA_DIR = Path(settings.CHROMA_PERSIST_DIR).resolve()
CHROMA_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# ChromaDB client singleton
# ─────────────────────────────────────────────────────────────────────────────

_chroma_client: chromadb.PersistentClient | None = None


def _get_client() -> chromadb.PersistentClient:
    """Return (or create) the module-level ChromaDB persistent client."""
    global _chroma_client
    if _chroma_client is None:
        logger.info(f"Connecting to ChromaDB at '{CHROMA_DIR}' …")
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
        logger.success("ChromaDB client ready.")
    return _chroma_client


# ─────────────────────────────────────────────────────────────────────────────
# Collection helpers
# ─────────────────────────────────────────────────────────────────────────────

def _collection_name(case_id: uuid.UUID) -> str:
    """
    Derive a deterministic, ChromaDB-safe collection name from a case UUID.

    ChromaDB requires names to match ``[a-zA-Z0-9_-]`` and be 3-63 chars.
    """
    return f"case_{str(case_id).replace('-', '_')}"


def _get_or_create_collection(
    case_id: uuid.UUID,
) -> chromadb.Collection:
    """Return the ChromaDB collection for *case_id*, creating it if absent."""
    client = _get_client()
    name   = _collection_name(case_id)

    collection = client.get_or_create_collection(
        name=name,
        metadata={
            "hnsw:space":           "cosine",   # use cosine similarity
            "hnsw:construction_ef": 128,
            "hnsw:M":               16,
        },
    )
    logger.debug(f"Collection '{name}': {collection.count()} existing vectors.")
    return collection


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion (add / upsert)
# ─────────────────────────────────────────────────────────────────────────────

def add_documents(
    chunks: List[Document],
    case_id: uuid.UUID,
    embedder: Optional[LawRAGEmbeddings] = None,
) -> int:
    """
    Embed *chunks* and upsert them into the per-case ChromaDB collection.

    Parameters
    ----------
    chunks  : list[Document]
        Output of :func:`~backend.rag.ingestion.ingest_pdf`.
    case_id : uuid.UUID
        Used to select / create the correct collection.
    embedder : LawRAGEmbeddings, optional
        Reuse a caller-provided instance to avoid repeated model look-ups.

    Returns
    -------
    int
        Number of chunks added.
    """
    if not chunks:
        logger.warning("add_documents called with empty chunk list — nothing to do.")
        return 0

    emb = embedder or get_embedder()
    collection = _get_or_create_collection(case_id)

    texts     = [c.page_content for c in chunks]
    metadatas = [c.metadata      for c in chunks]

    # Build deterministic IDs from doc_id + chunk_index so upsert is idempotent
    ids = [
        f"{m.get('doc_id', 'unknown')}__chunk_{m.get('chunk_index', i)}"
        for i, m in enumerate(metadatas)
    ]

    # Convert metadata values to Chroma-safe types (str/int/float/bool only)
    safe_metadatas = [_sanitise_metadata(m) for m in metadatas]

    logger.info(f"Embedding {len(texts)} chunks for case {str(case_id)[:8]}… …")
    vectors = emb.embed_documents(texts)

    logger.info("Upserting into ChromaDB …")
    collection.upsert(
        ids=ids,
        embeddings=vectors,
        documents=texts,
        metadatas=safe_metadatas,
    )

    logger.success(
        f"Upserted {len(chunks)} chunks into collection "
        f"'{_collection_name(case_id)}'. "
        f"Total collection size: {collection.count()}."
    )
    return len(chunks)


def _sanitise_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    ChromaDB only accepts str, int, float, and bool metadata values.
    Convert everything else to its string representation.
    """
    safe: Dict[str, Any] = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)):
            safe[k] = v
        else:
            safe[k] = str(v)
    return safe


# ─────────────────────────────────────────────────────────────────────────────
# Deletion
# ─────────────────────────────────────────────────────────────────────────────

def delete_document(doc_id: uuid.UUID, case_id: uuid.UUID) -> int:
    """
    Remove all chunks belonging to *doc_id* from the case collection.

    Returns the number of chunks deleted.
    """
    collection = _get_or_create_collection(case_id)
    prefix = str(doc_id)

    # Fetch IDs that start with doc_id prefix
    result = collection.get(where={"doc_id": str(doc_id)})
    ids_to_delete = result.get("ids", [])

    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
        logger.success(
            f"Deleted {len(ids_to_delete)} chunks for doc_id={str(doc_id)[:8]}… "
            f"from collection '{_collection_name(case_id)}'."
        )
    else:
        logger.warning(
            f"No chunks found for doc_id={str(doc_id)[:8]}… in case "
            f"'{_collection_name(case_id)}'."
        )

    return len(ids_to_delete)


# ─────────────────────────────────────────────────────────────────────────────
# Retrieval
# ─────────────────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    case_id: uuid.UUID,
    top_k: int = TOP_K,
    embedder: Optional[LawRAGEmbeddings] = None,
) -> List[Dict[str, Any]]:
    """
    Semantic search over all documents in a case's ChromaDB collection.

    Parameters
    ----------
    query   : str
        The user's natural-language question.
    case_id : uuid.UUID
        Limits search to this case's collection.
    top_k   : int
        Maximum number of chunks to return (default 5).
    embedder : LawRAGEmbeddings, optional
        Reuse a caller-provided instance.

    Returns
    -------
    list[dict]
        Each dict contains::

            {
                "doc_id":    str,
                "filename":  str,
                "page_num":  int,
                "score":     float,   # cosine similarity ∈ [0, 1]
                "excerpt":   str,     # the chunk text (first 400 chars)
                "content":   str,     # full chunk text
            }

        Results are sorted by descending score and filtered by
        ``SIMILARITY_THRESHOLD``.
    """
    emb = embedder or get_embedder()
    collection = _get_or_create_collection(case_id)

    if collection.count() == 0:
        logger.warning(
            f"Collection '{_collection_name(case_id)}' is empty — no results."
        )
        return []

    query_vector = emb.embed_query(query)

    raw = collection.query(
        query_embeddings=[query_vector],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    results: List[Dict[str, Any]] = []

    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    for doc_text, meta, dist in zip(documents, metadatas, distances):
        # ChromaDB cosine distance ∈ [0, 2]; convert to similarity ∈ [0, 1]
        similarity = max(0.0, 1.0 - (dist / 2.0))

        if similarity < SIMILARITY_THRESHOLD:
            continue  # skip low-quality matches

        results.append(
            {
                "doc_id":   meta.get("doc_id",   ""),
                "filename": meta.get("filename", ""),
                "page_num": int(meta.get("page_num", 0)),
                "score":    round(similarity, 4),
                "excerpt":  doc_text[:400],
                "content":  doc_text,
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)

    logger.debug(
        f"Retrieved {len(results)} chunks above threshold "
        f"(query={query[:60]!r}, case={str(case_id)[:8]}…)"
    )
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Collection stats (useful for diagnostics)
# ─────────────────────────────────────────────────────────────────────────────

def collection_stats(case_id: uuid.UUID) -> Dict[str, Any]:
    """Return basic statistics about a case's ChromaDB collection."""
    collection = _get_or_create_collection(case_id)
    return {
        "collection_name": _collection_name(case_id),
        "total_chunks":    collection.count(),
        "persist_dir":     str(CHROMA_DIR),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Full-corpus dump (used by Timeline Generator)
# ─────────────────────────────────────────────────────────────────────────────

def retrieve_all(case_id: uuid.UUID, batch_size: int = 500) -> List[Dict[str, Any]]:
    """
    Return **every** chunk stored in a case's ChromaDB collection.

    Unlike :func:`retrieve`, this function does NOT run a similarity query.
    It uses ``collection.get()`` to fetch all documents in batches, which is
    required by the Timeline Generator so it can read the entire document
    corpus and extract ALL date references — not just the top-K most
    similar to a single query.

    Parameters
    ----------
    case_id    : uuid.UUID
        Target case collection.
    batch_size : int
        Number of records to fetch per ChromaDB ``get()`` call (default 500).
        Increase for very large collections; decrease if memory is tight.

    Returns
    -------
    list[dict]
        Each dict contains::

            {
                "doc_id":   str,
                "filename": str,
                "page_num": int,
                "content":  str,   # full chunk text
            }

        Results are sorted by (filename, page_num, chunk_index) so the
        timeline prompt sees text in reading order.
    """
    collection = _get_or_create_collection(case_id)
    total      = collection.count()

    if total == 0:
        logger.warning(
            f"retrieve_all: collection '{_collection_name(case_id)}' is empty."
        )
        return []

    logger.info(
        f"retrieve_all: fetching {total} chunks from "
        f"'{_collection_name(case_id)}' in batches of {batch_size} …"
    )

    all_chunks: List[Dict[str, Any]] = []
    offset = 0

    while offset < total:
        batch = collection.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas"],
        )
        docs      = batch.get("documents", [])
        metadatas = batch.get("metadatas", [])

        for doc_text, meta in zip(docs, metadatas):
            all_chunks.append(
                {
                    "doc_id":      meta.get("doc_id",      ""),
                    "filename":    meta.get("filename",    ""),
                    "page_num":    int(meta.get("page_num",    0)),
                    "chunk_index": int(meta.get("chunk_index", 0)),
                    "content":     doc_text,
                }
            )
        offset += batch_size

    # Sort into reading order: filename → page → chunk position
    all_chunks.sort(key=lambda c: (c["filename"], c["page_num"], c["chunk_index"]))

    logger.success(
        f"retrieve_all: returned {len(all_chunks)} chunks for "
        f"case {str(case_id)[:8]}…"
    )
    return all_chunks

