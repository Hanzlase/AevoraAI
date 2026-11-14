"""Configuration settings for the Aevora AI RAG pipeline."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGSettings(BaseSettings):
    """Configurable parameters for embeddings, search, and storage."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Embedding model configuration
    embedding_model: str = Field(
        default="intfloat/multilingual-e5-small",
        description="HuggingFace model ID for multilingual dense embeddings",
    )
    embedding_device: str = Field(
        default="cpu",
        description="Compute device for embedding inference: 'cpu', 'cuda', or 'auto'",
    )
    query_prefix: str = Field(
        default="query: ",
        description="E5 prefix required for search queries",
    )
    passage_prefix: str = Field(
        default="passage: ",
        description="E5 prefix required for passages during indexing",
    )

    # Chunking parameters
    chunk_size: int = Field(
        default=500,
        description="Target maximum character size for PDF text chunks",
    )
    chunk_overlap: int = Field(
        default=100,
        description="Character overlap between consecutive chunks",
    )

    # Storage paths
    vector_store_dir: Path = Field(
        default=Path("data/vector_store"),
        description="Directory for persisting FAISS indexes and metadata",
    )
    documents_dir: Path = Field(
        default=Path("data/documents"),
        description="Directory containing source documents",
    )
    pdf_filename: str = Field(
        default="NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf",
        description="Human-readable PDF source document name",
    )
    json_filename: str = Field(
        default="NovaCare_RAG_Source_of_Truth.json",
        description="Canonical structured JSON source of truth filename",
    )

    # Search & fusion settings
    default_top_k: int = Field(
        default=5,
        description="Default number of ranked evidence chunks to retrieve",
    )
    rrf_k: int = Field(
        default=60,
        description="Reciprocal Rank Fusion smoothing parameter k",
    )
    vector_weight: float = Field(
        default=0.5,
        description="Weight multiplier for dense vector rank contribution",
    )
    keyword_weight: float = Field(
        default=0.5,
        description="Weight multiplier for sparse BM25 rank contribution",
    )
    insufficient_evidence_threshold: float = Field(
        default=0.015,
        description="RRF score threshold below which query is considered unanswerable",
    )

    @property
    def pdf_path(self) -> Path:
        return self.documents_dir / self.pdf_filename

    @property
    def json_path(self) -> Path:
        return self.documents_dir / self.json_filename

    @property
    def faiss_index_path(self) -> Path:
        return self.vector_store_dir / "faiss_index.bin"

    @property
    def chunks_metadata_path(self) -> Path:
        return self.vector_store_dir / "chunks_metadata.json"

    @property
    def bm25_corpus_path(self) -> Path:
        return self.vector_store_dir / "bm25_corpus.json"

    @property
    def manifest_path(self) -> Path:
        return self.vector_store_dir / "manifest.json"


@lru_cache
def get_rag_settings() -> RAGSettings:
    """Return cached RAG pipeline settings."""
    return RAGSettings()
