"""Retrieval evaluation runner and performance metric calculations."""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.rag.service import RAGService, get_rag_service

logger = logging.getLogger(__name__)


class QueryEvaluationResult(BaseModel):
    """Detailed evaluation result for a single benchmark query."""

    query_id: str
    language: str
    query: str
    is_answerable: bool
    is_held_out: bool
    detected_language: str
    insufficient_evidence: bool
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    reciprocal_rank: float
    top_chunk_id: str | None = None
    top_score: float | None = None
    matched_expected: bool


class LanguageCategoryMetric(BaseModel):
    """Aggregate metrics calculated for a specific language or query category."""

    language: str
    total_queries: int
    answerable_queries: int
    recall_at_3: float
    recall_at_5: float
    mrr: float


class EvaluationReport(BaseModel):
    """Comprehensive evaluation summary covering all benchmark questions."""

    total_queries: int
    answerable_count: int
    unanswerable_count: int
    overall_recall_at_3: float
    overall_recall_at_5: float
    overall_mrr: float
    unanswerable_correct_rejections: int
    unanswerable_rejection_rate: float
    by_language: dict[str, LanguageCategoryMetric] = Field(default_factory=dict)
    query_results: list[QueryEvaluationResult] = Field(default_factory=list)


class RAGEvaluator:
    """Evaluates RAG retrieval performance against standard benchmark question sets."""

    def __init__(
        self,
        rag_service: RAGService | None = None,
        dataset_path: Path | str = Path("data/evaluation_queries.json"),
    ) -> None:
        self.rag_service = rag_service or get_rag_service()
        self.dataset_path = Path(dataset_path)

    def load_dataset(self) -> list[dict[str, Any]]:
        """Load benchmark queries from JSON file."""
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Evaluation benchmark dataset not found at {self.dataset_path}"
            )
        with open(self.dataset_path, encoding="utf-8") as f:
            data = json.load(f)
        return data

    def evaluate(self, top_k: int = 5) -> EvaluationReport:
        """Run evaluation over the complete query set and compute Recall@k and MRR."""
        queries = self.load_dataset()
        results: list[QueryEvaluationResult] = []

        for q_entry in queries:
            qid = q_entry["query_id"]
            lang = q_entry["language"]
            query_text = q_entry["query"]
            is_answerable = q_entry.get("is_answerable", True)
            is_held_out = q_entry.get("is_held_out", False)
            expected_keywords = [kw.lower() for kw in q_entry.get("expected_keywords", [])]
            expected_entity = q_entry.get("expected_entity_id")

            # Execute RAG retrieval
            retrieval_res = self.rag_service.retrieve(query=query_text, top_k=top_k)
            evidence = retrieval_res.evidence

            r_at_1 = 0.0
            r_at_3 = 0.0
            r_at_5 = 0.0
            rr = 0.0
            matched = False

            if is_answerable:
                first_relevant_rank = None

                for rank_0, item in enumerate(evidence):
                    rank_1 = rank_0 + 1
                    text_lower = item.text.lower()

                    # Match condition: all expected keywords present or matching entity_id
                    entity_matched = bool(expected_entity and item.entity_id == expected_entity)
                    keywords_matched = bool(
                        expected_keywords
                        and sum(1 for kw in expected_keywords if kw in text_lower)
                        >= max(1, len(expected_keywords) // 2)
                    )

                    if entity_matched or keywords_matched:
                        if first_relevant_rank is None:
                            first_relevant_rank = rank_1
                        if rank_1 <= 1:
                            r_at_1 = 1.0
                        if rank_1 <= 3:
                            r_at_3 = 1.0
                        if rank_1 <= 5:
                            r_at_5 = 1.0

                if first_relevant_rank is not None:
                    rr = 1.0 / first_relevant_rank
                    matched = True
            else:
                # For unanswerable queries, success means correctly flagging insufficient_evidence
                matched = retrieval_res.insufficient_evidence

            top_id = evidence[0].chunk_id if evidence else None
            top_score = evidence[0].hybrid_score if evidence else None

            results.append(
                QueryEvaluationResult(
                    query_id=qid,
                    language=lang,
                    query=query_text,
                    is_answerable=is_answerable,
                    is_held_out=is_held_out,
                    detected_language=retrieval_res.detected_language,
                    insufficient_evidence=retrieval_res.insufficient_evidence,
                    recall_at_1=r_at_1,
                    recall_at_3=r_at_3,
                    recall_at_5=r_at_5,
                    reciprocal_rank=rr,
                    top_chunk_id=top_id,
                    top_score=top_score,
                    matched_expected=matched,
                )
            )

        # Aggregate metrics
        answerable_results = [r for r in results if r.is_answerable]
        unanswerable_results = [r for r in results if not r.is_answerable]

        ans_count = len(answerable_results)
        unans_count = len(unanswerable_results)

        overall_r3 = (
            (sum(r.recall_at_3 for r in answerable_results) / ans_count) if ans_count else 0.0
        )
        overall_r5 = (
            (sum(r.recall_at_5 for r in answerable_results) / ans_count) if ans_count else 0.0
        )
        overall_mrr = (
            (sum(r.reciprocal_rank for r in answerable_results) / ans_count) if ans_count else 0.0
        )

        unans_correct = sum(1 for r in unanswerable_results if r.matched_expected)
        unans_rate = (unans_correct / unans_count) if unans_count else 1.0

        # Language-grouped metrics
        by_language: dict[str, LanguageCategoryMetric] = {}
        distinct_langs = {r.language for r in results if r.is_answerable}

        for lang in distinct_langs:
            lang_records = [r for r in answerable_results if r.language == lang]
            total_in_lang = sum(1 for r in results if r.language == lang)
            l_count = len(lang_records)
            l_r3 = (sum(r.recall_at_3 for r in lang_records) / l_count) if l_count else 0.0
            l_r5 = (sum(r.recall_at_5 for r in lang_records) / l_count) if l_count else 0.0
            l_mrr = (sum(r.reciprocal_rank for r in lang_records) / l_count) if l_count else 0.0

            by_language[lang] = LanguageCategoryMetric(
                language=lang,
                total_queries=total_in_lang,
                answerable_queries=l_count,
                recall_at_3=round(l_r3, 4),
                recall_at_5=round(l_r5, 4),
                mrr=round(l_mrr, 4),
            )

        return EvaluationReport(
            total_queries=len(results),
            answerable_count=ans_count,
            unanswerable_count=unans_count,
            overall_recall_at_3=round(overall_r3, 4),
            overall_recall_at_5=round(overall_r5, 4),
            overall_mrr=round(overall_mrr, 4),
            unanswerable_correct_rejections=unans_correct,
            unanswerable_rejection_rate=round(unans_rate, 4),
            by_language=by_language,
            query_results=results,
        )
