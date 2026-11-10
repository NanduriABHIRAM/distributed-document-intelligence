"""FAISS-backed dense retrieval with an explicit vector-position to chunk mapping."""

from __future__ import annotations

import numpy as np


class VectorRetriever:
    def __init__(self, index=None, embedder=None):
        self.index = index
        self.embedder = embedder
        self.records: list[dict] = []

    def fit(self, chunks: list[dict]) -> None:
        if self.embedder is None:
            raise ValueError("VectorRetriever requires an embedder before fitting.")
        vectors = self.embedder.encode([chunk.get("text", "") for chunk in chunks])
        if not len(vectors):
            self.index, self.records = None, []
            return
        import faiss
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        self.records = list(chunks)

    def search(self, query: str, top_k: int = 100) -> list[dict]:
        if self.index is None or self.embedder is None or not self.records or top_k < 1:
            return []
        vector = self.embedder.encode([query])
        scores, positions = self.index.search(vector, min(top_k, len(self.records)))
        results = []
        for rank, (score, position) in enumerate(zip(scores[0], positions[0]), start=1):
            if position < 0:
                continue
            record = dict(self.records[int(position)])
            record.update({"id": record.get("chunk_id", str(position)), "vector_score": float(score), "vector_rank": rank})
            results.append(record)
        return results
