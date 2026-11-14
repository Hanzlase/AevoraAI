"""Hybrid retrieval-augmented generation (RAG) pipeline package (Phase 02)."""

from app.rag.config import RAGSettings, get_rag_settings
from app.rag.evaluation import EvaluationReport, RAGEvaluator
from app.rag.ingestion import IngestionPipeline
from app.rag.schemas import ChunkMetadata, IngestionReport, RetrievalItem, RetrievalResult
from app.rag.service import RAGService, get_rag_service

__all__ = [
    "ChunkMetadata",
    "EvaluationReport",
    "IngestionReport",
    "IngestionPipeline",
    "RAGEvaluator",
    "RAGService",
    "RAGSettings",
    "RetrievalItem",
    "RetrievalResult",
    "get_rag_service",
    "get_rag_settings",
]
