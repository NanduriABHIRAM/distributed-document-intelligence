"""Composable BM25 + dense retrieval using reproducible reciprocal-rank fusion."""

from __future__ import annotations

from retrieval.rrf import reciprocal_rank_fusion


class HybridRetriever:
    def __init__(self, lexical, dense=None, rrf_k: int = 60):
        self.lexical = lexical
        self.dense = dense
        self.rrf_k = rrf_k

    def search(self, query: str, top_k: int = 10) -> tuple[list[dict], dict]:
        lexical = self.lexical.search(query, top_k=max(top_k * 10, 100))
        dense = self.dense.search(query, top_k=max(top_k * 10, 100)) if self.dense else []
        result_lists = [lexical, dense] if dense else [lexical]
        results = reciprocal_rank_fusion(result_lists, k=self.rrf_k)
        return results[:top_k], {
            "mode": "hybrid_rrf" if dense else "bm25_only",
            "rrf_k": self.rrf_k,
            "lexical_candidates": len(lexical),
            "dense_candidates": len(dense),
        }
