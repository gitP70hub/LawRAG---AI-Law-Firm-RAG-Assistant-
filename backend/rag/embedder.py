"""
backend/rag/embedder.py
=======================
API-based embeddings using HuggingFace Inference API.
Removes local dependency on torch and sentence-transformers.
"""

from typing import List
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from loguru import logger
from core.config import settings

class LawRAGEmbeddings(Embeddings):
    """
    LangChain-compatible embeddings class backed by HuggingFace Inference API.
    """

    def __init__(self):
        if not settings.HUGGINGFACE_API_TOKEN:
            logger.warning("HUGGINGFACE_API_TOKEN is missing in environment variables!")
        
        self.client = HuggingFaceEndpointEmbeddings(
            model=settings.EMBEDDING_MODEL_ID,
            huggingfacehub_api_token=settings.HUGGINGFACE_API_TOKEN,
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        logger.info(f"Generating embeddings via API for {len(texts)} chunks...")
        return self.client.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self.client.embed_query(text)

def get_embedder() -> LawRAGEmbeddings:
    """Return a ready-to-use LawRAGEmbeddings instance."""
    return LawRAGEmbeddings()
