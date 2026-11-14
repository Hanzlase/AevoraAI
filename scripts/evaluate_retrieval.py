"""CLI script to run retrieval evaluation against benchmark questions and print metrics."""

import sys

from app.rag.evaluation import RAGEvaluator
from app.rag.service import get_rag_service


def main() -> None:
    service = get_rag_service()
    if not service.is_indexed():
        print("[ERROR] Index files not found. Run 'python -m scripts.ingest_knowledge_base' first.")
        sys.exit(1)

    print("=" * 70)
    print("Aevora AI — Retrieval Evaluation Benchmark")
    print("=" * 70)

    evaluator = RAGEvaluator(rag_service=service)
    report = evaluator.evaluate(top_k=5)

    print(f"Total Benchmark Queries:   {report.total_queries}")
    print(f"Answerable Queries:        {report.answerable_count}")
    print(f"Unanswerable Queries:      {report.unanswerable_count}")
    print("-" * 70)
    r3_pct = report.overall_recall_at_3 * 100
    r5_pct = report.overall_recall_at_5 * 100
    print(f"Overall Recall@3:          {report.overall_recall_at_3:.4f} ({r3_pct:.1f}%)")
    print(f"Overall Recall@5:          {report.overall_recall_at_5:.4f} ({r5_pct:.1f}%)")
    print(f"Overall MRR:               {report.overall_mrr:.4f}")
    unans_pct = report.unanswerable_rejection_rate * 100
    print(
        f"Unanswerable Rejection:    {report.unanswerable_correct_rejections}/"
        f"{report.unanswerable_count} ({unans_pct:.1f}%)"
    )
    print("-" * 70)
    print("Metrics by Language / Script Category:")
    header = (
        f"{'Language':<15} {'Total':<8} {'Answerable':<12} "
        f"{'Recall@3':<12} {'Recall@5':<12} {'MRR':<8}"
    )
    print(header)
    print("-" * 70)

    for lang, m in report.by_language.items():
        row = (
            f"{lang:<15} {m.total_queries:<8} {m.answerable_queries:<12} "
            f"{m.recall_at_3:<12.4f} {m.recall_at_5:<12.4f} {m.mrr:<8.4f}"
        )
        print(row)

    print("=" * 70)

    # Detailed query breakdown
    print("\nDetailed Query Results:")
    for qr in report.query_results:
        status_str = "PASS" if qr.matched_expected else "FAIL"
        held_out_str = "[HELD-OUT]" if qr.is_held_out else "[DEV]"
        q_snippet = qr.query[:40]
        print(
            f"  [{status_str}] {qr.query_id:<8} {held_out_str:<11} {qr.language:<12} | "
            f"{q_snippet:<40} | R@5={qr.recall_at_5} RR={qr.reciprocal_rank:.2f}"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()
