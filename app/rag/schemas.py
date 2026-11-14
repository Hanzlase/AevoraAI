"""Data models and schemas for the Aevora AI RAG pipeline."""

from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal["json", "pdf"]
LanguageLabel = Literal["en", "ur", "roman_ur", "mixed", "unknown"]


class ChunkMetadata(BaseModel):
    """Normalized document chunk with full lineage and metadata."""

    chunk_id: str = Field(..., description="Deterministic unique identifier for this chunk")
    text: str = Field(..., description="Normalized textual content of the chunk")
    source_type: SourceType = Field(..., description="Origin source type: json or pdf")
    source_file: str = Field(..., description="Filename of origin document")
    json_pointer: str | None = Field(
        default=None, description="JSON pointer path if derived from JSON"
    )
    page_number: int | None = Field(
        default=None, description="1-based page number if derived from PDF"
    )
    section: str = Field(default="general", description="Clinic section or topic")
    category: str = Field(
        default="clinic_info", description="Category: doctor, service, policy, faq, etc."
    )
    entity_id: str | None = Field(
        default=None, description="Identifier of associated entity (e.g., doctor_id)"
    )
    language_hint: str = Field(default="en", description="Primary language or script of the chunk")
    provenance: list[str] = Field(
        default_factory=list, description="Human-readable provenance references"
    )


class RetrievalItem(BaseModel):
    """An individual retrieved evidence item with hybrid ranking scores."""

    chunk_id: str
    text: str
    source_type: SourceType
    source_file: str
    page_number: int | None = None
    json_pointer: str | None = None
    section: str
    category: str
    entity_id: str | None = None
    vector_rank: int | None = None
    vector_score: float | None = None
    keyword_rank: int | None = None
    keyword_score: float | None = None
    hybrid_score: float = Field(..., description="Reciprocal Rank Fusion score")
    provenance: list[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    """The complete response from the RAG retrieval service."""

    query: str = Field(..., description="Original raw user query")
    normalized_query: str = Field(..., description="Cleaned, normalized query string")
    detected_language: LanguageLabel = Field(..., description="Detected script/language category")
    evidence: list[RetrievalItem] = Field(
        default_factory=list, description="Ranked evidence records"
    )
    insufficient_evidence: bool = Field(
        default=False, description="Flag indicating no evidence met the threshold"
    )
    top_k: int = Field(default=5, description="Requested top-k items")
    retrieval_method: str = Field(
        default="hybrid_rrf_v1", description="Identifier of the retrieval algorithm"
    )
    dataset_version: str = Field(default="1.0.0", description="Version of the indexed dataset")


class ConsistencyIssue(BaseModel):
    """Discrepancy or warning detected between JSON and PDF sources."""

    field: str
    json_value: Any
    pdf_value: Any
    description: str
    severity: Literal["warning", "conflict"] = "warning"


class IngestionReport(BaseModel):
    """Detailed summary report generated following corpus ingestion."""

    dataset_name: str
    dataset_version: str
    json_records_processed: int
    pdf_pages_processed: int
    pdf_empty_pages: list[int] = Field(default_factory=list)
    total_chunks_created: int
    duplicate_chunks_merged: int
    consistency_issues: list[ConsistencyIssue] = Field(default_factory=list)
    faiss_index_path: str
    bm25_corpus_path: str
    built_at: str
    status: Literal["success", "partial", "failed"] = "success"


class DatasetManifest(BaseModel):
    """Index metadata and integrity manifest stored alongside the vector index."""

    dataset_name: str
    dataset_version: str
    source_file_hashes: dict[str, str]
    embedding_model: str
    embedding_dim: int
    chunk_count: int
    chunk_size: int
    chunk_overlap: int
    built_at: str
    consistency_issues: list[ConsistencyIssue] = Field(default_factory=list)
