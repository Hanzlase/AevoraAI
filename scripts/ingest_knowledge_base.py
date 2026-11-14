"""CLI script to ingest clinic PDF/JSON sources and build FAISS and BM25 indexes."""

import sys

from app.rag.config import get_rag_settings
from app.rag.ingestion import IngestionPipeline


def main() -> None:
    settings = get_rag_settings()
    print("=" * 70)
    print("Aevora AI — Clinic Knowledge Base Ingestion")
    print("=" * 70)
    print(f"JSON Source:       {settings.json_path}")
    print(f"PDF Source:        {settings.pdf_path}")
    print(f"Embedding Model:   {settings.embedding_model}")
    print(f"Target Device:     {settings.embedding_device}")
    print(f"Index Destination: {settings.vector_store_dir}")
    print("-" * 70)

    pipeline = IngestionPipeline(settings=settings)

    try:
        report = pipeline.run()
        print("\n[SUCCESS] Ingestion completed successfully!")
        print(f"Dataset Name:            {report.dataset_name} (v{report.dataset_version})")
        print(f"JSON Chunks Processed:   {report.json_records_processed}")
        print(f"PDF Pages Processed:     {report.pdf_pages_processed}")
        if report.pdf_empty_pages:
            print(f"PDF Low-Text Pages:      {report.pdf_empty_pages}")
        print(f"Total Unique Chunks:     {report.total_chunks_created}")
        print(f"Duplicates Merged:       {report.duplicate_chunks_merged}")
        print(f"FAISS Index Path:        {report.faiss_index_path}")
        print(f"BM25 Corpus Path:        {report.bm25_corpus_path}")

        if report.consistency_issues:
            print(f"\n[WARNING] {len(report.consistency_issues)} consistency notes detected:")
            for issue in report.consistency_issues:
                print(f"  - [{issue.severity.upper()}] {issue.field}: {issue.description}")
        else:
            print("\n[OK] Zero source consistency conflicts detected.")

        print("=" * 70)
        sys.exit(0)

    except Exception as exc:
        print(f"\n[ERROR] Ingestion failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
