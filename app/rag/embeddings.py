"""Singleton multilingual E5 embedding service with passage/query prefixing."""

import logging
from typing import Optional

import numpy as np

from app.rag.config import RAGSettings, get_rag_settings

logger = logging.getLogger(__name__)

_EMBEDDING_SERVICE_INSTANCE: Optional["EmbeddingService"] = None


class EmbeddingService:
    """Manages dense vector encoding using intfloat/multilingual-e5-small."""

    def __init__(self, settings: RAGSettings | None = None) -> None:
        self.settings = settings or get_rag_settings()
        self.model_name = self.settings.embedding_model
        self.device = self._resolve_device(self.settings.embedding_device)
        self.query_prefix = self.settings.query_prefix
        self.passage_prefix = self.settings.passage_prefix
        self._model = None

    def _resolve_device(self, requested_device: str) -> str:
        """Resolve device string: 'cpu', 'cuda', or 'auto'."""
        req = requested_device.lower()
        if req == "cpu":
            return "cpu"
        try:
            import torch

            if torch.cuda.is_available() and req in ("cuda", "auto"):
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    @property
    def model(self):
        """Lazy loader for SentenceTransformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info(
                "Loading embedding model '%s' on device '%s'...",
                self.model_name,
                self.device,
            )
            self._model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("Embedding model '%s' successfully loaded.", self.model_name)
        return self._model

    def embed_passages(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Embed document passages for indexing, applying the 'passage: ' prefix.

        Returns:
            np.ndarray: 2D array of shape (N, dim), L2-normalized.
        """
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        prefixed_texts = [f"{self.passage_prefix}{text}" for text in texts]
        embeddings = self.model.encode(
            prefixed_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a user query for search, applying the 'query: ' prefix.

        Returns:
            np.ndarray: 1D array of shape (dim,), L2-normalized.
        """
        prefixed_query = f"{self.query_prefix}{query}"
        embedding = self.model.encode(
            [prefixed_query],
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embedding[0].astype(np.float32)


def get_embedding_service(settings: RAGSettings | None = None) -> EmbeddingService:
    """Provide singleton instance of EmbeddingService."""
    global _EMBEDDING_SERVICE_INSTANCE
    if _EMBEDDING_SERVICE_INSTANCE is None:
        _EMBEDDING_SERVICE_INSTANCE = EmbeddingService(settings)
    return _EMBEDDING_SERVICE_INSTANCE
