"""
backend/modules/precedent_finder.py
=====================================
Precedent Finder — LexAI's Indian case-law semantic search module.

Overview
--------
This module maintains a **dedicated ChromaDB collection** named
``indian_case_laws`` pre-populated with 5+ seed Indian Supreme Court /
High Court judgment summaries.  When a user describes their legal issue,
the module:

1. Encodes the query with the same embedding model used site-wide.
2. Performs a cosine-similarity search against the ``indian_case_laws``
   collection to retrieve the top-K most relevant seed entries.
3. Passes those retrieved summaries + the user's query to the LLM which
   re-scores each case and enriches the response with plain-English
   relevance explanations.
4. Returns a validated ``list[Precedent]`` sorted by ``relevance_score``
   descending.

Seed data
---------
Five representative Indian Supreme Court / High Court judgments are
auto-seeded into ChromaDB on first import.  The seeding is idempotent
(guarded by a collection-count check).

Token logging
-------------
All LLM calls log an estimated token count derived from ``len(text) / 4``
(a standard approximation for English/legal text).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEndpoint
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, field_validator

from core.config import settings
from prompts.precedent_prompt import (
    PRECEDENT_HUMAN_PROMPT,
    PRECEDENT_SYSTEM_PROMPT,
)
from rag.embedder import get_embedder

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

PRECEDENT_COLLECTION_NAME = "indian_case_laws"
MAX_PARSE_RETRIES         = 3
TOP_K_RETRIEVE            = 8   # chromadb results fed to LLM for re-ranking

# ─────────────────────────────────────────────────────────────────────────────
# Seed data — 5 Indian Supreme Court / High Court landmark judgments
# ─────────────────────────────────────────────────────────────────────────────

SEED_JUDGMENTS: List[Dict[str, Any]] = [
    {
        "id": "seed_001",
        "case_name": "Vishaka v. State of Rajasthan",
        "court": "Supreme Court of India",
        "year": 1997,
        "citation": "AIR 1997 SC 3011",
        "summary": (
            "A landmark PIL filed by women's rights groups following the gang-rape of "
            "social activist Bhanwari Devi. The Supreme Court held that sexual harassment "
            "at the workplace violates Articles 14, 15, 19, and 21 of the Constitution. "
            "The Court laid down binding guidelines (Vishaka Guidelines) for employers to "
            "prevent and redress sexual harassment, filling the legislative vacuum until "
            "the POSH Act 2013 was enacted."
        ),
        "key_ruling": (
            "Sexual harassment at the workplace constitutes a violation of fundamental "
            "rights and employers have a duty to provide a safe working environment; "
            "Vishaka Guidelines are binding on all employers until legislation is enacted."
        ),
        "clause_types": "employment, fundamental rights, sexual harassment, workplace safety",
    },
    {
        "id": "seed_002",
        "case_name": "Maneka Gandhi v. Union of India",
        "court": "Supreme Court of India",
        "year": 1978,
        "citation": "AIR 1978 SC 597",
        "summary": (
            "The petitioner's passport was impounded under the Passport Act without "
            "giving her a hearing. The Supreme Court held that Article 21 (right to life "
            "and personal liberty) is not limited to mere animal existence and encompasses "
            "the right to live with human dignity. The Court expanded the scope of Article 21 "
            "to include the right to travel abroad and held that any law curtailing it must "
            "satisfy the test of reasonableness under Articles 14 and 19 as well."
        ),
        "key_ruling": (
            "Article 21 must be read conjunctively with Articles 14 and 19; a law depriving "
            "personal liberty must be fair, just, and reasonable — not merely procedurally "
            "valid — establishing the 'golden triangle' of fundamental rights."
        ),
        "clause_types": "constitutional law, personal liberty, fundamental rights, natural justice",
    },
    {
        "id": "seed_003",
        "case_name": "Satyam Infoway Ltd. v. Siffunet Solutions Pvt. Ltd.",
        "court": "Supreme Court of India",
        "year": 2004,
        "citation": "(2004) 6 SCC 145",
        "summary": (
            "A domain-name dispute where the plaintiff sought an injunction against the "
            "defendant's use of a confusingly similar domain name. The Supreme Court held "
            "that domain names are not mere addresses but can be protected as trademarks "
            "under the Trade Marks Act 1999 and the common law of passing off. The Court "
            "applied the 'likelihood of confusion' test to domain names for the first time "
            "in India, bringing them within the ambit of intellectual property protection."
        ),
        "key_ruling": (
            "A domain name is a business identifier that can be protected under trademark "
            "law; the test for infringement is whether the defendant's domain is likely to "
            "cause confusion or deception in the minds of the public."
        ),
        "clause_types": "intellectual property, trademark, domain name, passing off, IP",
    },
    {
        "id": "seed_004",
        "case_name": "Shayara Bano v. Union of India",
        "court": "Supreme Court of India",
        "year": 2017,
        "citation": "(2017) 9 SCC 1",
        "summary": (
            "A five-judge constitutional bench examined the practice of instantaneous triple "
            "talaq (talaq-e-biddat) under Muslim personal law. Three of five judges held the "
            "practice to be unconstitutional as it is manifestly arbitrary under Article 14 "
            "and violates the fundamental right of Muslim women. The majority declared the "
            "practice void. Parliament subsequently codified the ban in the Muslim Women "
            "(Protection of Rights on Marriage) Act 2019."
        ),
        "key_ruling": (
            "Instantaneous triple talaq is manifestly arbitrary and unconstitutional under "
            "Article 14 of the Constitution; personal law practices that violate fundamental "
            "rights are subject to constitutional scrutiny."
        ),
        "clause_types": "family law, constitutional law, personal law, divorce, fundamental rights",
    },
    {
        "id": "seed_005",
        "case_name": "ONGC Ltd. v. Saw Pipes Ltd.",
        "court": "Supreme Court of India",
        "year": 2003,
        "citation": "(2003) 5 SCC 705",
        "summary": (
            "A commercial dispute arising from liquidated damages claimed by ONGC for delayed "
            "delivery of pipes. The arbitral tribunal rejected the claim; ONGC challenged the "
            "award. The Supreme Court held that the 'public policy' ground under Section 34 "
            "of the Arbitration and Conciliation Act 1996 includes awards that are 'patently "
            "illegal' or contrary to the provisions of any Indian statute, significantly "
            "broadening courts' power to set aside arbitral awards in India."
        ),
        "key_ruling": (
            "An arbitral award is contrary to public policy if it is patently illegal or "
            "in contravention of the substantive provisions of Indian law; courts may set "
            "aside such awards under Section 34 of the Arbitration Act."
        ),
        "clause_types": "arbitration, commercial law, liquidated damages, contract, dispute resolution",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic model — Precedent
# ─────────────────────────────────────────────────────────────────────────────

class Precedent(BaseModel):
    """A single Indian court precedent returned by the finder."""

    case_name: str = Field(
        ...,
        description="Full case name, e.g. 'Vishaka v. State of Rajasthan'.",
    )
    court: str = Field(
        ...,
        description="Court name, e.g. 'Supreme Court of India'.",
    )
    year: int = Field(
        ...,
        ge=1947,
        le=2100,
        description="Year of the judgment.",
    )
    citation: str = Field(
        default="",
        description="AIR / SCC citation string.",
    )
    summary: str = Field(
        ...,
        min_length=20,
        description="2–4 sentence factual and legal summary.",
    )
    key_ruling: str = Field(
        ...,
        min_length=10,
        description="Core legal principle / ratio decidendi.",
    )
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Semantic relevance to the user's legal issue.",
    )
    relevance_reason: str = Field(
        default="",
        description="Why this case is relevant to the user's issue.",
    )

    @field_validator("relevance_score", mode="before")
    @classmethod
    def coerce_score(cls, v: Any) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.5

    @field_validator("year", mode="before")
    @classmethod
    def coerce_year(cls, v: Any) -> int:
        try:
            return int(v)
        except (TypeError, ValueError):
            return 2000


# ─────────────────────────────────────────────────────────────────────────────
# ChromaDB — dedicated precedent collection
# ─────────────────────────────────────────────────────────────────────────────

_precedent_collection: chromadb.Collection | None = None


def _get_precedent_collection() -> chromadb.Collection:
    """Return (and lazily create + seed) the indian_case_laws ChromaDB collection."""
    global _precedent_collection
    if _precedent_collection is not None:
        return _precedent_collection

    from pathlib import Path
    chroma_dir = Path(settings.CHROMA_PERSIST_DIR).resolve()
    chroma_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
    )

    collection = client.get_or_create_collection(
        name=PRECEDENT_COLLECTION_NAME,
        metadata={
            "hnsw:space":           "cosine",
            "hnsw:construction_ef": 128,
            "hnsw:M":               16,
        },
    )

    # Seed if empty
    if collection.count() == 0:
        logger.info(
            f"Seeding '{PRECEDENT_COLLECTION_NAME}' with "
            f"{len(SEED_JUDGMENTS)} judgments …"
        )
        _seed_collection(collection)
    else:
        logger.debug(
            f"Precedent collection '{PRECEDENT_COLLECTION_NAME}' already has "
            f"{collection.count()} entries — skipping seed."
        )

    _precedent_collection = collection
    return collection


def _seed_collection(collection: chromadb.Collection) -> None:
    """Embed and upsert seed judgments into the collection."""
    emb = get_embedder()

    texts = [
        (
            f"{j['case_name']} ({j['year']}) — {j['court']}. "
            f"{j['summary']} Key ruling: {j['key_ruling']} "
            f"Topics: {j.get('clause_types', '')}"
        )
        for j in SEED_JUDGMENTS
    ]

    vectors   = emb.embed_documents(texts)
    ids       = [j["id"] for j in SEED_JUDGMENTS]
    metadatas = [
        {
            "case_name":  j["case_name"],
            "court":      j["court"],
            "year":       str(j["year"]),
            "citation":   j.get("citation", ""),
            "summary":    j["summary"],
            "key_ruling": j["key_ruling"],
        }
        for j in SEED_JUDGMENTS
    ]

    collection.upsert(
        ids=ids,
        embeddings=vectors,
        documents=texts,
        metadatas=metadatas,
    )
    logger.success(
        f"Seeded {len(SEED_JUDGMENTS)} judgments into '{PRECEDENT_COLLECTION_NAME}'."
    )


# ─────────────────────────────────────────────────────────────────────────────
# LLM singleton
# ─────────────────────────────────────────────────────────────────────────────

_llm: HuggingFaceEndpoint | None = None


def _get_llm() -> HuggingFaceEndpoint:
    global _llm
    if _llm is None:
        logger.info(
            f"PrecedentFinder: initialising LLM '{settings.LLM_MODEL_ID}' …"
        )
        _llm = HuggingFaceEndpoint(
            repo_id=settings.LLM_MODEL_ID,
            huggingfacehub_api_token=settings.HUGGINGFACE_API_TOKEN,
            task="text-generation",
            max_new_tokens=2048,
            do_sample=False,
            temperature=0.01,
            repetition_penalty=1.05,
            return_full_text=False,
        )
        logger.success("PrecedentFinder LLM ready.")
    return _llm


# ─────────────────────────────────────────────────────────────────────────────
# LangChain chain
# ─────────────────────────────────────────────────────────────────────────────

def _build_chain():
    """Return an LCEL chain: prompt | llm | str_parser."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PRECEDENT_SYSTEM_PROMPT),
            ("human",  PRECEDENT_HUMAN_PROMPT),
        ]
    )
    return RunnablePassthrough() | prompt | _get_llm() | StrOutputParser()


# ─────────────────────────────────────────────────────────────────────────────
# JSON parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

class _JSONParseError(Exception):
    """Raised when the LLM response cannot be parsed as a JSON array."""


def _extract_json_array(raw_text: str) -> List[Any]:
    """Strip prose/fences and extract the first JSON array from raw_text."""
    text = raw_text.strip()
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*", "", text)

    start = text.find("[")
    end   = text.rfind("]")

    if start == -1 or end == -1 or end <= start:
        raise _JSONParseError(
            f"No JSON array delimiters found. First 200 chars: {text[:200]!r}"
        )

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise _JSONParseError(f"JSON decode error: {exc}") from exc

    if not isinstance(parsed, list):
        raise _JSONParseError(
            f"Parsed JSON is not an array (got {type(parsed).__name__})."
        )

    return parsed


def _parse_precedents(raw_text: str) -> List[Precedent]:
    """Parse LLM output and validate each item as a Precedent."""
    raw_list = _extract_json_array(raw_text)
    results: List[Precedent] = []

    for i, item in enumerate(raw_list):
        if not isinstance(item, dict):
            logger.warning(f"Precedent item {i} is not a dict — skipping.")
            continue
        try:
            results.append(Precedent(**item))
        except (ValidationError, TypeError) as exc:
            logger.warning(f"Precedent item {i} validation failed: {exc} — skipping.")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Context builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_context(chroma_results: Dict[str, Any]) -> str:
    """Format raw ChromaDB query results into a numbered context block."""
    documents = chroma_results.get("documents", [[]])[0]
    metadatas = chroma_results.get("metadatas", [[]])[0]
    distances = chroma_results.get("distances", [[]])[0]

    lines: List[str] = []
    for i, (doc, meta, dist) in enumerate(
        zip(documents, metadatas, distances), start=1
    ):
        similarity = round(max(0.0, 1.0 - dist / 2.0), 4)
        lines.append(
            f"[{i}] {meta.get('case_name', 'Unknown')} ({meta.get('year', '?')}) "
            f"— {meta.get('court', '?')}\n"
            f"    Citation : {meta.get('citation', 'N/A')}\n"
            f"    Cosine   : {similarity}\n"
            f"    Summary  : {meta.get('summary', doc[:300])}\n"
            f"    Key Ruling: {meta.get('key_ruling', '')}\n"
        )
    return "\n".join(lines) if lines else "No cases retrieved."


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def find_precedents(
    query: str,
    top_k: int = 5,
) -> List[Precedent]:
    """
    Find Indian court precedents semantically similar to *query*.

    Pipeline
    --------
    1. Embed *query* with the shared LexAI embedder.
    2. Query the ``indian_case_laws`` ChromaDB collection for top-K cases.
    3. Format retrieved cases as a numbered context block.
    4. Call the LLM with ``PRECEDENT_SYSTEM_PROMPT`` to re-score and enrich
       each case.
    5. Parse, validate, and sort results by ``relevance_score`` descending.

    Parameters
    ----------
    query : str
        Natural-language description of the user's legal issue.
    top_k : int
        Maximum number of precedents to return (default 5).

    Returns
    -------
    list[Precedent]
        Validated, relevance-sorted precedents. Empty list on failure.
    """
    logger.info(f"PrecedentFinder: query={query[:80]!r} top_k={top_k}")

    # ── 1. Embed query & retrieve from ChromaDB ───────────────────────────────
    try:
        collection = _get_precedent_collection()
        emb        = get_embedder()
        query_vec  = emb.embed_query(query)

        n_results = min(TOP_K_RETRIEVE, collection.count())
        raw = collection.query(
            query_embeddings=[query_vec],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.error(f"ChromaDB query failed: {exc}", exc_info=True)
        return []

    # ── 2. Build context ──────────────────────────────────────────────────────
    context = _build_context(raw)
    logger.debug(f"Precedent context built ({len(context)} chars).")

    # ── 3. Estimate & log token count ─────────────────────────────────────────
    approx_tokens = len(context) // 4 + len(query) // 4
    logger.info(f"PrecedentFinder: estimated input tokens ≈ {approx_tokens:,}")

    # ── 4. LLM call with retry ────────────────────────────────────────────────
    chain   = _build_chain()
    results: List[Precedent] = []

    for attempt in range(1, MAX_PARSE_RETRIES + 1):
        try:
            logger.info(
                f"PrecedentFinder LLM call — attempt {attempt}/{MAX_PARSE_RETRIES} …"
            )
            raw_answer: str = await chain.ainvoke(
                {"context": context, "question": query}
            )

            output_tokens = len(raw_answer) // 4
            logger.info(
                f"PrecedentFinder LLM responded. "
                f"Output ≈ {output_tokens} tokens. "
                f"Total ≈ {approx_tokens + output_tokens} tokens."
            )
            logger.debug(f"Raw LLM output (first 400 chars): {raw_answer[:400]!r}")

            results = _parse_precedents(raw_answer)
            logger.success(
                f"Parsed {len(results)} precedents on attempt {attempt}."
            )
            break

        except _JSONParseError as exc:
            logger.warning(f"PrecedentFinder attempt {attempt} parse error: {exc}")
            if attempt == MAX_PARSE_RETRIES:
                logger.error("All parse attempts exhausted — returning empty list.")
                return []

        except Exception as exc:
            logger.error(
                f"Unexpected error on attempt {attempt}: {exc}", exc_info=True
            )
            if attempt == MAX_PARSE_RETRIES:
                return []

    # ── 5. Filter, sort, cap ──────────────────────────────────────────────────
    results = [p for p in results if p.relevance_score > 0.3]
    results.sort(key=lambda p: p.relevance_score, reverse=True)
    results = results[:top_k]

    logger.success(
        f"PrecedentFinder complete: {len(results)} precedents returned."
    )
    return results
