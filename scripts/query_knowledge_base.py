"""CLI utility to execute a test retrieval query against the indexed clinic corpus."""

import sys

from app.rag.service import get_rag_service


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m scripts.query_knowledge_base "<query>" [top_k]')
        print('Example: python -m scripts.query_knowledge_base "Dr Sana Malik ki fee kitni hai?"')
        sys.exit(1)

    query = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    service = get_rag_service()
    if not service.is_indexed():
        print("[ERROR] Index files not found. Run 'python -m scripts.ingest_knowledge_base' first.")
        sys.exit(1)

    result = service.retrieve(query=query, top_k=top_k)

    print("=" * 70)
    print("Aevora AI — Knowledge Base Retrieval Query")
    print("=" * 70)
    print(f"Query:               {result.query}")
    print(f"Normalized:          {result.normalized_query}")
    print(f"Detected Script:     {result.detected_language}")
    print(f"Evidence Sufficient: {not result.insufficient_evidence}")
    print(f"Algorithm:           {result.retrieval_method} (top_k={result.top_k})")
    print("-" * 70)

    if result.insufficient_evidence or not result.evidence:
        print("\n[NOTE] Insufficient evidence found in clinic knowledge base for this query.")
    else:
        for idx, item in enumerate(result.evidence, start=1):
            print(f"\n--- Rank #{idx} (Hybrid Score: {item.hybrid_score:.4f}) ---")
            print(f"Chunk ID:     {item.chunk_id}")
            print(f"Source Type:  {item.source_type.upper()} ({item.source_file})")
            print(f"Section:      {item.section} (Category: {item.category})")
            score_line = (
                f"Scores:       Vector Rank={item.vector_rank} ({item.vector_score:.4f}), "
                f"BM25 Rank={item.keyword_rank} ({item.keyword_score:.2f})"
            )
            print(score_line)
            print("Provenance:   " + " | ".join(item.provenance))
            print("Evidence:\n" + item.text)

    print("=" * 70)


if __name__ == "__main__":
    main()
