"""
backend/rag/ingestion.py
========================
PDF ingestion pipeline for LexAI.

Responsibilities
----------------
* Open PDFs with PyMuPDF (fitz) — page-level text extraction.
* Pre-process legal text: strip running headers/footers, normalise whitespace,
  remove artefacts (page numbers, exhibit markers, etc.).
* Split into overlapping chunks with LangChain RecursiveCharacterTextSplitter.
* Return LangChain Document objects ready for embedding.

Dependencies: pymupdf, langchain-text-splitters
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

CHUNK_SIZE    = 1000   # characters per chunk
CHUNK_OVERLAP = 200    # characters of overlap between consecutive chunks

# Legal-document noise patterns compiled once at module load.
_HEADER_FOOTER_PATTERNS: List[re.Pattern] = [
    # Standalone page numbers:  "- 3 -"  |  "Page 3 of 12"
    re.compile(r"^\s*[-–—]?\s*\d+\s*[-–—]?\s*$", re.MULTILINE),
    re.compile(r"^\s*page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE | re.MULTILINE),
    # Confidentiality banners repeated on every page
    re.compile(r"CONFIDENTIAL\s*[-–—]?\s*(ATTORNEY.CLIENT PRIVILEGE)?",
               re.IGNORECASE),
    # ALL-CAPS short lines (≤ 6 words) that appear at top/bottom — typical headers
    re.compile(r"^([A-Z][A-Z\s,\.]{2,60})\n", re.MULTILINE),
    # Exhibit markers: "EXHIBIT A", "Attachment 3"
    re.compile(r"^\s*(EXHIBIT|ATTACHMENT|ANNEX|SCHEDULE)\s+[A-Z0-9]+\s*$",
               re.IGNORECASE | re.MULTILINE),
    # Bates stamps: "ABC000123"
    re.compile(r"\b[A-Z]{2,8}\d{5,10}\b"),
    # Multiple blank lines → single blank line
    re.compile(r"\n{3,}"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Text cleaning
# ─────────────────────────────────────────────────────────────────────────────

def _clean_legal_text(raw: str) -> str:
    """
    Apply a sequence of regex substitutions to strip legal-document noise.

    Processing order matters:
    1. Remove page-number lines (must precede blank-line collapse).
    2. Remove confidentiality banners.
    3. Remove all-caps short headers.
    4. Remove Bates stamps / exhibit markers.
    5. Collapse excessive blank lines.
    6. Strip leading/trailing whitespace per line and globally.
    """
    text = raw

    # 1 & 2 & 3 & 4 — noise removal
    text = _HEADER_FOOTER_PATTERNS[0].sub("", text)   # standalone page numbers
    text = _HEADER_FOOTER_PATTERNS[1].sub("", text)   # "Page X of Y"
    text = _HEADER_FOOTER_PATTERNS[2].sub("", text)   # confidentiality banners
    text = _HEADER_FOOTER_PATTERNS[3].sub("\n", text) # ALL-CAPS short headers
    text = _HEADER_FOOTER_PATTERNS[4].sub("", text)   # exhibit markers
    text = _HEADER_FOOTER_PATTERNS[5].sub("", text)   # bates stamps

    # Fix ligatures and non-breaking spaces common in PDF extraction
    text = text.replace("\ufb01", "fi").replace("\ufb02", "fl")
    text = text.replace("\xa0", " ").replace("\u2019", "'")

    # Strip trailing whitespace on every line
    text = "\n".join(line.rstrip() for line in text.splitlines())

    # 5 — collapse blank lines
    text = _HEADER_FOOTER_PATTERNS[6].sub("\n\n", text)

    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# PDF loader
# ─────────────────────────────────────────────────────────────────────────────

def load_pdf_pages(file_path: Path) -> List[Document]:
    """
    Open *file_path* with PyMuPDF and return one :class:`~langchain.schema.Document`
    per page, with rich metadata attached.

    Metadata keys
    -------------
    source      : str  — absolute file path
    filename    : str  — base filename
    page_num    : int  — 1-based page number
    total_pages : int  — total pages in the document
    """
    if not file_path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    docs: List[Document] = []

    with fitz.open(str(file_path)) as pdf:
        total_pages = pdf.page_count
        logger.info(f"[PyMuPDF] Opening '{file_path.name}' — {total_pages} pages")

        for page_index in range(total_pages):
            page = pdf[page_index]

            # Extract text blocks (more reliable than get_text("text") for layouts)
            raw_text = page.get_text("text", sort=True)  # sort=True → reading order
            cleaned  = _clean_legal_text(raw_text)

            if not cleaned.strip():
                logger.debug(f"  Page {page_index + 1}: empty after cleaning, skipping.")
                continue

            docs.append(
                Document(
                    page_content=cleaned,
                    metadata={
                        "source":      str(file_path.resolve()),
                        "filename":    file_path.name,
                        "page_num":    page_index + 1,
                        "total_pages": total_pages,
                    },
                )
            )

    logger.success(
        f"[PyMuPDF] Extracted {len(docs)} non-empty pages from '{file_path.name}'."
    )
    return docs


# ─────────────────────────────────────────────────────────────────────────────
# Splitter
# ─────────────────────────────────────────────────────────────────────────────

def _build_splitter() -> RecursiveCharacterTextSplitter:
    """
    Return a :class:`RecursiveCharacterTextSplitter` tuned for legal documents.

    Separator priority (tried in order):
    1. Double newline  → paragraph break
    2. Single newline  → line break
    3. ". "            → sentence boundary (keeps trailing period on left chunk)
    4. " "             → word boundary (last resort — avoids mid-word splits)
    5. ""              → character-level fallback
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
        is_separator_regex=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def ingest_pdf(
    file_path: Path,
    doc_id: uuid.UUID,
    case_id: uuid.UUID,
) -> List[Document]:
    """
    Full ingestion pipeline for a single PDF.

    Steps
    -----
    1. Load pages with PyMuPDF.
    2. Split into overlapping chunks.
    3. Enrich chunk metadata with ``doc_id``, ``case_id``, and ``chunk_index``.

    Parameters
    ----------
    file_path : Path
        Absolute path to the PDF on disk.
    doc_id : uuid.UUID
        The :class:`~backend.api.models.db_models.Document` primary key so
        chunks can be traced back to their DB record.
    case_id : uuid.UUID
        The parent :class:`~backend.api.models.db_models.Case` ID used as
        the ChromaDB collection namespace.

    Returns
    -------
    List[Document]
        LangChain Document objects ready to be embedded and upserted into
        ChromaDB.
    """
    logger.info(f"ingest_pdf: starting for '{file_path.name}'")
    pages    = load_pdf_pages(file_path)
    logger.info(f"ingest_pdf: {len(pages)} pages loaded, splitting into chunks …")
    splitter = _build_splitter()
    chunks   = splitter.split_documents(pages)

    doc_id_str  = str(doc_id)
    case_id_str = str(case_id)

    for idx, chunk in enumerate(chunks):
        chunk.metadata.update(
            {
                "doc_id":      doc_id_str,
                "case_id":     case_id_str,
                "chunk_index": idx,
                "chunk_total": len(chunks),
            }
        )

    logger.success(
        f"ingest_pdf: '{file_path.name}' → {len(chunks)} chunks "
        f"(doc_id={doc_id_str[:8]}…, case_id={case_id_str[:8]}…, "
        f"chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})"
    )
    return chunks
