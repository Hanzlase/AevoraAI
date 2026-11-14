"""Hybrid search combiner using Reciprocal Rank Fusion (RRF) and evidence deduplication."""

import logging
from typing import Any

from app.rag.config import RAGSettings, get_rag_settings
from app.rag.keyword_search import BM25KeywordSearch
from app.rag.normalization import detect_language_script, normalize_unicode
from app.rag.schemas import ChunkMetadata, RetrievalItem, RetrievalResult
from app.rag.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class HybridSearchService:
    """Combines dense vector retrieval and sparse BM25 keyword search via RRF."""

    def __init__(
        self,
        vector_store: FAISSVectorStore,
        keyword_search: BM25KeywordSearch,
        settings: RAGSettings | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.keyword_search = keyword_search
        self.settings = settings or get_rag_settings()

    def fuse_rrf(
        self,
        vector_results: list[tuple[ChunkMetadata, float, int]],
        keyword_results: list[tuple[ChunkMetadata, float, int]],
        top_k: int = 5,
        dataset_version: str = "1.0.0",
    ) -> list[RetrievalItem]:
        """Combine rankings using Reciprocal Rank Fusion (RRF)."""
        k = self.settings.rrf_k
        w_vec = self.settings.vector_weight
        w_kw = self.settings.keyword_weight

        # Track metadata and scores keyed by chunk_id
        chunk_map: dict[str, ChunkMetadata] = {}
        vector_info: dict[str, tuple[int, float]] = {}
        keyword_info: dict[str, tuple[int, float]] = {}
        rrf_scores: dict[str, float] = {}

        for chunk, score, rank in vector_results:
            cid = chunk.chunk_id
            chunk_map[cid] = chunk
            vector_info[cid] = (rank, score)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (w_vec * (1.0 / (k + rank)))

        for chunk, score, rank in keyword_results:
            cid = chunk.chunk_id
            chunk_map[cid] = chunk
            keyword_info[cid] = (rank, score)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (w_kw * (1.0 / (k + rank)))

        # Sort candidate chunks by descending combined RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        items: list[RetrievalItem] = []
        for cid in sorted_ids[:top_k]:
            chunk = chunk_map[cid]
            v_rank, v_score = vector_info.get(cid, (None, None))
            k_rank, k_score = keyword_info.get(cid, (None, None))
            score = rrf_scores[cid]

            items.append(
                RetrievalItem(
                    chunk_id=cid,
                    text=chunk.text,
                    source_type=chunk.source_type,
                    source_file=chunk.source_file,
                    page_number=chunk.page_number,
                    json_pointer=chunk.json_pointer,
                    section=chunk.section,
                    category=chunk.category,
                    entity_id=chunk.entity_id,
                    vector_rank=v_rank,
                    vector_score=v_score,
                    keyword_rank=k_rank,
                    keyword_score=k_score,
                    hybrid_score=round(score, 6),
                    provenance=list(chunk.provenance),
                )
            )

        return items

    def search(
        self,
        query: str,
        query_vector: Any,
        top_k: int = 5,
        dataset_version: str = "1.0.0",
    ) -> RetrievalResult:
        """Execute hybrid search pipeline and evaluate evidence sufficiency."""
        raw_query = query
        normalized_query = normalize_unicode(query)
        detected_lang = detect_language_script(raw_query)

        # Retrieve candidates from both search methods
        # Search slightly more than top_k to permit optimal fusion
        candidate_k = max(top_k * 2, 10)
        vector_results = self.vector_store.search(query_vector, top_k=candidate_k)
        keyword_results = self.keyword_search.search(normalized_query, top_k=candidate_k)

        evidence = self.fuse_rrf(
            vector_results=vector_results,
            keyword_results=keyword_results,
            top_k=top_k,
            dataset_version=dataset_version,
        )

        # Evaluate evidence sufficiency against calibrated threshold
        # If no evidence retrieved, or top hybrid score is below threshold, flag insufficient
        insufficient = False
        if not evidence:
            insufficient = True
        else:
            top_item = evidence[0]
            # Flag insufficient if top RRF score is below threshold
            if top_item.hybrid_score < self.settings.insufficient_evidence_threshold:
                insufficient = True
            # Flag insufficient if no strong keyword match and vector score is below bound
            elif (top_item.keyword_score is None or top_item.keyword_score < 2.0) and (
                top_item.vector_score is None or top_item.vector_score < 0.84
            ):
                insufficient = True

        return RetrievalResult(
            query=raw_query,
            normalized_query=normalized_query,
            detected_language=detected_lang,
            evidence=evidence,
            insufficient_evidence=insufficient,
            top_k=top_k,
            retrieval_method="hybrid_rrf_v1",
            dataset_version=dataset_version,
        )
