"""Public retrieval service providing hybrid RAG access to NovaCare knowledge base."""

import logging
from typing import Optional

from app.rag.config import RAGSettings, get_rag_settings
from app.rag.embeddings import EmbeddingService, get_embedding_service
from app.rag.hybrid_search import HybridSearchService
from app.rag.keyword_search import BM25KeywordSearch
from app.rag.schemas import RetrievalResult
from app.rag.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)

_RAG_SERVICE_INSTANCE: Optional["RAGService"] = None


class RAGService:
    """Public high-level RAG retrieval service for conversational and workflow agents."""

    def __init__(
        self,
        settings: RAGSettings | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_store: FAISSVectorStore | None = None,
        keyword_search: BM25KeywordSearch | None = None,
    ) -> None:
        self.settings = settings or get_rag_settings()
        self.embedding_service = embedding_service or get_embedding_service(self.settings)
        self.vector_store = vector_store or FAISSVectorStore(self.settings)
        self.keyword_search = keyword_search or BM25KeywordSearch(self.settings)
        self.hybrid_search = HybridSearchService(
            vector_store=self.vector_store,
            keyword_search=self.keyword_search,
            settings=self.settings,
        )
        self._dataset_version = "1.0.0"

    def is_indexed(self) -> bool:
        """Check if index files exist and are ready for retrieval."""
        return (
            self.settings.faiss_index_path.exists()
            and self.settings.chunks_metadata_path.exists()
            and self.settings.bm25_corpus_path.exists()
        )

    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        """Retrieve most relevant grounded clinic evidence for a user query.

        Args:
            query: User question in English, Urdu script, Roman Urdu, or mixed.
            top_k: Number of ranked evidence records to return (defaults to configured top_k).

        Returns:
            RetrievalResult containing ranked evidence items, language hint, and metadata.
        """
        k = top_k if top_k is not None else self.settings.default_top_k

        # Encode query using multilingual-e5-small query prefix
        query_vector = self.embedding_service.embed_query(query)

        # Run hybrid retrieval
        return self.hybrid_search.search(
            query=query,
            query_vector=query_vector,
            top_k=k,
            dataset_version=self._dataset_version,
        )


def get_rag_service(settings: RAGSettings | None = None) -> RAGService:
    """Return singleton instance of RAGService."""
    global _RAG_SERVICE_INSTANCE
    if _RAG_SERVICE_INSTANCE is None:
        _RAG_SERVICE_INSTANCE = RAGService(settings)
    return _RAG_SERVICE_INSTANCE
