"""BM25 sparse keyword retrieval service supporting English, Urdu, and Roman Urdu."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from app.rag.config import RAGSettings, get_rag_settings
from app.rag.normalization import expand_query_aliases, tokenize_for_bm25
from app.rag.schemas import ChunkMetadata

logger = logging.getLogger(__name__)


class RobustBM25Okapi(BM25Okapi):
    """BM25Okapi extension ensuring all matching terms have a non-negative contribution."""

    def _calc_idf(self, nd):
        super()._calc_idf(nd)
        # Ensure terms present in corpus have a strictly positive floor IDF
        # (Standard Lucene/BM25+ protection against negative term weights on small corpora)
        for word, val in self.idf.items():
            if val <= 0.0:
                self.idf[word] = 0.1


class BM25KeywordSearch:
    """Sparse keyword search using BM25Okapi over tokenized multilingual chunks."""

    def __init__(self, settings: RAGSettings | None = None) -> None:
        self.settings = settings or get_rag_settings()
        self.corpus_path = self.settings.bm25_corpus_path
        self._bm25: BM25Okapi | None = None
        self._chunks: list[ChunkMetadata] = []
        self._corpus_tokens: list[list[str]] = []

    @property
    def is_loaded(self) -> bool:
        """Check if BM25 model and corpus are ready in memory."""
        return self._bm25 is not None and len(self._chunks) > 0

    def build_and_save(self, chunks: list[ChunkMetadata]) -> None:
        """Tokenize chunks, instantiate BM25Okapi, and persist corpus atomically as JSON."""
        logger.info("Building BM25 corpus for %d chunks...", len(chunks))
        corpus_tokens = [tokenize_for_bm25(c.text) for c in chunks]

        # Instantiate BM25
        self._bm25 = RobustBM25Okapi(corpus_tokens)
        self._chunks = chunks
        self._corpus_tokens = corpus_tokens

        # Persist transparent JSON representation
        self.settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
        serializable_corpus = [
            {
                "chunk": c.model_dump(),
                "tokens": tokens,
            }
            for c, tokens in zip(chunks, corpus_tokens, strict=False)
        ]

        with tempfile.NamedTemporaryFile(
            dir=self.settings.vector_store_dir,
            delete=False,
            suffix=".tmp",
            mode="w",
            encoding="utf-8",
        ) as tmp_f:
            json.dump(serializable_corpus, tmp_f, ensure_ascii=False, indent=2)
            tmp_path = Path(tmp_f.name)

        tmp_path.replace(self.corpus_path)
        logger.info("BM25 corpus successfully saved at %s", self.corpus_path)

    def load(self) -> None:
        """Load persisted JSON corpus and rebuild BM25Okapi index in memory."""
        if not self.corpus_path.exists():
            raise FileNotFoundError(
                f"BM25 corpus file not found at {self.corpus_path}. "
                "Run 'python -m scripts.ingest_knowledge_base' to construct it."
            )

        logger.info("Loading BM25 corpus from %s...", self.corpus_path)
        with open(self.corpus_path, encoding="utf-8") as f:
            raw_data: list[dict[str, Any]] = json.load(f)

        self._chunks = [ChunkMetadata.model_validate(item["chunk"]) for item in raw_data]
        self._corpus_tokens = [item["tokens"] for item in raw_data]
        self._bm25 = RobustBM25Okapi(self._corpus_tokens)
        logger.info("BM25 index successfully built from %d chunks.", len(self._chunks))

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[tuple[ChunkMetadata, float, int]]:
        """Perform BM25 scoring with query alias expansion.

        Returns:
            list of (ChunkMetadata, bm25_score, rank_1_based)
        """
        if not self.is_loaded:
            self.load()

        assert self._bm25 is not None
        expanded_query = expand_query_aliases(query)
        query_tokens = tokenize_for_bm25(expanded_query)

        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        # Filter indices with positive non-zero score
        scored_indices = [(idx, float(score)) for idx, score in enumerate(scores) if score > 0.0]
        # Sort descending by score
        scored_indices.sort(key=lambda x: x[1], reverse=True)

        results: list[tuple[ChunkMetadata, float, int]] = []
        for rank_0, (idx, score) in enumerate(scored_indices[:top_k]):
            chunk = self._chunks[idx]
            results.append((chunk, score, rank_0 + 1))

        return results
