"""Ingestion pipeline coordinator for NovaCare clinic PDF and JSON documents."""

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.rag.chunking import (
    build_pdf_chunks,
    check_source_consistency,
    merge_and_deduplicate_chunks,
)
from app.rag.config import RAGSettings, get_rag_settings
from app.rag.embeddings import EmbeddingService, get_embedding_service
from app.rag.json_loader import JSONSourceLoader
from app.rag.keyword_search import BM25KeywordSearch
from app.rag.pdf_loader import PDFSourceLoader
from app.rag.schemas import DatasetManifest, IngestionReport
from app.rag.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file for integrity tracking."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class IngestionPipeline:
    """Orchestrates end-to-end ingestion, chunking, consistency checking, and indexing."""

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

    def run(self, force_reindex: bool = False) -> IngestionReport:
        """Run complete extraction, chunking, and dual-index construction."""
        pdf_path = self.settings.pdf_path
        json_path = self.settings.json_path

        # 1. Validate source files exist
        if not json_path.exists():
            raise FileNotFoundError(f"Missing canonical JSON source at: {json_path}")
        if not pdf_path.exists():
            raise FileNotFoundError(f"Missing human-readable PDF source at: {pdf_path}")

        json_hash = compute_file_sha256(json_path)
        pdf_hash = compute_file_sha256(pdf_path)

        logger.info("Ingesting clinic sources: JSON=%s, PDF=%s", json_path.name, pdf_path.name)

        # 2. Extract structured JSON records
        json_loader = JSONSourceLoader(json_path)
        raw_json_data = json_loader.load_raw()
        dataset_name = raw_json_data.get("dataset_name", "NovaCare Medical Centre")
        dataset_version = raw_json_data.get("dataset_version", "1.0.0")
        json_chunks = json_loader.extract_chunks()

        # 3. Extract PDF pages
        pdf_loader = PDFSourceLoader(pdf_path)
        extracted_pages = pdf_loader.extract_pages()
        low_text_pages = [p.page_number for p in extracted_pages if p.is_low_text]
        pdf_full_text = "\n".join(p.normalized_text for p in extracted_pages)

        # 4. Consistency checks between JSON and PDF
        consistency_issues = check_source_consistency(raw_json_data, pdf_full_text)
        if consistency_issues:
            logger.warning(
                "Detected %d consistency issues between JSON and PDF", len(consistency_issues)
            )
            for issue in consistency_issues:
                logger.warning(
                    "[%s] %s: %s", issue.severity.upper(), issue.field, issue.description
                )

        # 5. Chunk PDF and merge with JSON chunks
        pdf_chunks = build_pdf_chunks(
            pages=extracted_pages,
            source_filename=pdf_path.name,
            target_size=self.settings.chunk_size,
            overlap=self.settings.chunk_overlap,
        )

        all_chunks, duplicates_merged = merge_and_deduplicate_chunks(json_chunks, pdf_chunks)
        total_chunks = len(all_chunks)
        logger.info(
            "Created %d total chunks (%d JSON, %d PDF, %d merged)",
            total_chunks,
            len(json_chunks),
            len(pdf_chunks),
            duplicates_merged,
        )

        # 6. Generate embeddings for all chunks
        chunk_texts = [c.text for c in all_chunks]
        logger.info(
            "Computing dense embeddings for %d chunks using '%s'...",
            total_chunks,
            self.settings.embedding_model,
        )
        embeddings = self.embedding_service.embed_passages(chunk_texts)

        # 7. Build Manifest
        now_iso = datetime.now(UTC).isoformat()
        manifest = DatasetManifest(
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            source_file_hashes={
                json_path.name: json_hash,
                pdf_path.name: pdf_hash,
            },
            embedding_model=self.settings.embedding_model,
            embedding_dim=embeddings.shape[1],
            chunk_count=total_chunks,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            built_at=now_iso,
            consistency_issues=consistency_issues,
        )

        # 8. Build & Save FAISS Index
        self.vector_store.build_and_save(
            embeddings=embeddings,
            chunks=all_chunks,
            manifest=manifest,
        )

        # 9. Build & Save BM25 Corpus
        self.keyword_search.build_and_save(all_chunks)

        report = IngestionReport(
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            json_records_processed=len(json_chunks),
            pdf_pages_processed=len(extracted_pages),
            pdf_empty_pages=low_text_pages,
            total_chunks_created=total_chunks,
            duplicate_chunks_merged=duplicates_merged,
            consistency_issues=consistency_issues,
            faiss_index_path=str(self.settings.faiss_index_path),
            bm25_corpus_path=str(self.settings.bm25_corpus_path),
            built_at=now_iso,
            status="success",
        )

        logger.info(
            "Ingestion complete. Status: %s. Chunks: %d", report.status, report.total_chunks_created
        )
        return report
