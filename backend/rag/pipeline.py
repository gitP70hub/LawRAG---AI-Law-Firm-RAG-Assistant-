"""
backend/rag/pipeline.py
=======================
LangChain LCEL RAG pipeline for LexAI.

Architecture
------------

    User question
         │
         ▼
    [Retriever]  ──►  top-5 relevant chunks (from ChromaDB, per-case)
         │
         ▼
    [PromptTemplate]  ──►  legal-domain system prompt + context + question
         │
         ▼
    [HuggingFace Router (OpenAI-compat)]  ──►  Qwen2.5-7B-Instruct
         │
         ▼
    [StrOutputParser]  ──►  answer string
         │
         ▼
    [post-processor]  ──►  {"answer": str, "sources": list[dict]}

Design decisions
----------------
* Uses the NEW HuggingFace Inference Router (router.huggingface.co/v1) which
  exposes an OpenAI-compatible chat/completions endpoint.  The old
  api-inference.huggingface.co endpoint now returns 404 for all 7B models.
* ``langchain_openai.ChatOpenAI`` is used as the client — it speaks
  OpenAI-style chat completions natively, so no custom wrapper is needed.
* The LCEL chain is built once per call — stateless and thread-safe.
* ``run_rag_query`` is the single public entry-point for the chat router.

Dependencies: langchain, langchain-openai, langchain-core
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from loguru import logger

from core.config import settings
from prompts.system_prompts import CLIENT_PROMPT, get_prompt
from rag.embedder import get_embedder
from rag.retriever import retrieve

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_SYSTEM_PROMPT = CLIENT_PROMPT
HUMAN_TEMPLATE        = "Context:\n{context}\n\nQuestion: {question}"

# New HuggingFace OpenAI-compatible router base URL
HF_ROUTER_BASE_URL = "https://router.huggingface.co/v1"


# ─────────────────────────────────────────────────────────────────────────────
# LLM singleton
# ─────────────────────────────────────────────────────────────────────────────

_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    """Return (or build) the HuggingFace router LLM client (OpenAI-compatible)."""
    global _llm
    if _llm is None:
        logger.info(
            f"Initialising LLM '{settings.LLM_MODEL_ID}' "
            f"via HF Router (OpenAI-compat) …"
        )
        _llm = ChatOpenAI(
            model=settings.LLM_MODEL_ID,
            openai_api_key=settings.HUGGINGFACE_API_TOKEN,
            openai_api_base=HF_ROUTER_BASE_URL,
            max_tokens=1024,
            temperature=0.1,
        )
        logger.success("LLM ready.")
    return _llm


# ─────────────────────────────────────────────────────────────────────────────
# Prompt
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(system_prompt: str | None = None) -> ChatPromptTemplate:
    """Build a ChatPromptTemplate from the given (or default) system prompt."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt or DEFAULT_SYSTEM_PROMPT),
            ("human",  HUMAN_TEMPLATE),
        ]
    )


# ─────────────────────────────────────────────────────────────────────────────
# Context formatting
# ─────────────────────────────────────────────────────────────────────────────

def _format_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Render retrieved chunks into a numbered context block for the prompt.

    Each chunk is formatted as::

        [1] SOURCE: contract.pdf | PAGE: 3
        ---
        <chunk text>

    This makes it easy for the LLM to produce inline citations.
    """
    if not chunks:
        return "No relevant documents found."

    lines: List[str] = []
    for i, chunk in enumerate(chunks, start=1):
        filename = chunk.get("filename", "unknown")
        page_num = chunk.get("page_num", "?")
        content  = chunk.get("content",  "")
        lines.append(
            f"[{i}] SOURCE: {filename} | PAGE: {page_num}\n"
            f"---\n"
            f"{content}\n"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def run_rag_query(
    question: str,
    case_id: uuid.UUID,
    top_k: int = 5,
    chat_history: List[Dict[str, str]] | None = None,
    prompt_type: str = "client",
) -> Dict[str, Any]:
    """
    Execute the full RAG pipeline for a single user question.

    Parameters
    ----------
    question     : str
        The user's natural-language question.
    case_id      : uuid.UUID
        Used to scope retrieval to this case's ChromaDB collection.
    top_k        : int
        Number of chunks to retrieve (default 5).
    chat_history : list[dict], optional
        Previous ``[{"role": "user"|"assistant", "content": "…"}, …]``
        entries — currently passed through for future multi-turn support.

    Returns
    -------
    dict
        ``{"answer": str, "sources": list[dict]}``

        ``sources`` is the list returned by
        :func:`~backend.rag.retriever.retrieve`, each item containing
        ``doc_id``, ``filename``, ``page_num``, ``score``, ``excerpt``.
    """
    logger.info(
        f"RAG query | case={str(case_id)[:8]}… | "
        f"question={question[:80]!r}"
    )

    # ── 1. Retrieve ───────────────────────────────────────────────────────────
    embedder = get_embedder()
    chunks   = retrieve(question, case_id, top_k=top_k, embedder=embedder)
    context  = _format_context(chunks)

    logger.debug(f"Retrieved {len(chunks)} chunks.")

    # ── 2. Build LCEL chain ───────────────────────────────────────────────────
    try:
        system_prompt = get_prompt(prompt_type)
    except KeyError:
        logger.warning(
            f"Unknown prompt_type '{prompt_type}', falling back to 'client'."
        )
        system_prompt = DEFAULT_SYSTEM_PROMPT

    prompt = _build_prompt(system_prompt)
    llm    = _get_llm()
    parser = StrOutputParser()

    chain = (
        RunnablePassthrough()          # passes the input dict through unchanged
        | prompt                       # renders system + human messages
        | llm                          # calls HF Router (OpenAI-compat)
        | parser                       # extracts text from the LLM response
    )

    # ── 3. Invoke ─────────────────────────────────────────────────────────────
    logger.info("Invoking LLM …")
    answer: str = await chain.ainvoke(
        {
            "context":  context,
            "question": question,
        }
    )
    answer = answer.strip()

    logger.success(f"LLM answered ({len(answer)} chars).")

    # ── 4. Build source list (strip full content to keep response lean) ───────
    sources = [
        {
            "doc_id":   c["doc_id"],
            "filename": c["filename"],
            "page_num": c["page_num"],
            "score":    c["score"],
            "excerpt":  c["excerpt"],
        }
        for c in chunks
    ]

    return {"answer": answer, "sources": sources}
