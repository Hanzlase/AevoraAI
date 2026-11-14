"""FAISS vector store indexer, persistence manager, and search service."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from app.rag.config import RAGSettings, get_rag_settings
from app.rag.schemas import ChunkMetadata, DatasetManifest

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """Manages dense vector indexing, storage, and retrieval using FAISS CPU."""

    def __init__(self, settings: RAGSettings | None = None) -> None:
        self.settings = settings or get_rag_settings()
        self.index_path = self.settings.faiss_index_path
        self.metadata_path = self.settings.chunks_metadata_path
        self.manifest_path = self.settings.manifest_path
        self._index = None
        self._chunks: list[ChunkMetadata] = []
        self._id_to_chunk: dict[str, ChunkMetadata] = {}

    @property
    def is_loaded(self) -> bool:
        """Check if index and metadata are currently loaded in memory."""
        return self._index is not None and len(self._chunks) > 0

    def build_and_save(
        self,
        embeddings: np.ndarray,
        chunks: list[ChunkMetadata],
        manifest: DatasetManifest,
    ) -> None:
        """Build FAISS FlatIP index from normalized vectors and persist atomically to disk."""
        import faiss

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks count ({len(chunks)}) does not match embeddings count ({len(embeddings)})"
            )

        dim = embeddings.shape[1]
        logger.info(
            "Building FAISS IndexFlatIP with %d vectors of dimension %d...", len(chunks), dim
        )

        # Create Flat Inner Product index (equivalent to cosine similarity on normalized vectors)
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings.astype(np.float32))

        # Ensure target storage directory exists
        self.settings.vector_store_dir.mkdir(parents=True, exist_ok=True)

        # Atomic write of FAISS index file
        with tempfile.NamedTemporaryFile(
            dir=self.settings.vector_store_dir, delete=False, suffix=".tmp"
        ) as tmp_f:
            tmp_index_path = Path(tmp_f.name)

        try:
            faiss.write_index(index, str(tmp_index_path))
            tmp_index_path.replace(self.index_path)
        except Exception:
            if tmp_index_path.exists():
                tmp_index_path.unlink()
            raise

        # Save chunk metadata in row-order
        chunks_payload = [c.model_dump() for c in chunks]
        with tempfile.NamedTemporaryFile(
            dir=self.settings.vector_store_dir,
            delete=False,
            suffix=".tmp",
            mode="w",
            encoding="utf-8",
        ) as tmp_meta:
            json.dump(chunks_payload, tmp_meta, ensure_ascii=False, indent=2)
            tmp_meta_path = Path(tmp_meta.name)

        tmp_meta_path.replace(self.metadata_path)

        # Save manifest
        with tempfile.NamedTemporaryFile(
            dir=self.settings.vector_store_dir,
            delete=False,
            suffix=".tmp",
            mode="w",
            encoding="utf-8",
        ) as tmp_man:
            json.dump(manifest.model_dump(), tmp_man, ensure_ascii=False, indent=2)
            tmp_man_path = Path(tmp_man.name)

        tmp_man_path.replace(self.manifest_path)

        # Update in-memory state
        self._index = index
        self._chunks = chunks
        self._id_to_chunk = {c.chunk_id: c for c in chunks}
        logger.info("FAISS vector store successfully persisted at %s", self.index_path)

    def load(self) -> None:
        """Load persisted FAISS index, row-ordered metadata, and validate integrity."""
        import faiss

        if not self.index_path.exists() or not self.metadata_path.exists():
            raise FileNotFoundError(
                f"Vector store files missing at {self.index_path}. "
                "Run 'python -m scripts.ingest_knowledge_base' to build them."
            )

        logger.info("Loading FAISS index from %s...", self.index_path)
        self._index = faiss.read_index(str(self.index_path))

        with open(self.metadata_path, encoding="utf-8") as f:
            raw_metadata: list[dict[str, Any]] = json.load(f)

        self._chunks = [ChunkMetadata.model_validate(c) for c in raw_metadata]
        self._id_to_chunk = {c.chunk_id: c for c in self._chunks}

        if self._index.ntotal != len(self._chunks):
            raise ValueError(
                f"FAISS index count ({self._index.ntotal}) != metadata count ({len(self._chunks)})"
            )

        logger.info("FAISS vector store loaded successfully (%d chunks).", len(self._chunks))

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
    ) -> list[tuple[ChunkMetadata, float, int]]:
        """Search nearest chunks by cosine similarity using query embedding vector.

        Returns:
            list of (ChunkMetadata, similarity_score, rank_index_1_based)
        """
        if not self.is_loaded:
            self.load()

        assert self._index is not None
        k = min(top_k, len(self._chunks))
        if k <= 0:
            return []

        # Ensure vector shape (1, dim)
        if query_vector.ndim == 1:
            query_vector = np.expand_dims(query_vector, axis=0)

        scores, indices = self._index.search(query_vector.astype(np.float32), k)

        results: list[tuple[ChunkMetadata, float, int]] = []
        for rank_0, (score, row_id) in enumerate(zip(scores[0], indices[0], strict=False)):
            if row_id < 0 or row_id >= len(self._chunks):
                continue
            chunk = self._chunks[row_id]
            results.append((chunk, float(score), rank_0 + 1))

        return results

    def get_chunk_by_id(self, chunk_id: str) -> ChunkMetadata | None:
        """Look up chunk by its deterministic unique ID."""
        if not self.is_loaded:
            self.load()
        return self._id_to_chunk.get(chunk_id)

    @property
    def chunks(self) -> list[ChunkMetadata]:
        """Return list of loaded chunks."""
        if not self.is_loaded:
            self.load()
        return self._chunks
