"""A deterministic BM25 baseline that keeps every result tied to its chunk."""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    return re.findall(r"[\w'-]+", text.casefold(), flags=re.UNICODE)


class BM25Retriever:
    def __init__(self) -> None:
        self._chunks: list[dict] = []
        self._index: BM25Okapi | None = None

    def fit(self, chunks: list[dict]) -> None:
        self._chunks = list(chunks)
        corpus = [tokenize(chunk.get("text", "")) for chunk in self._chunks]
        self._index = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, top_k: int = 100) -> list[dict]:
        if not self._index or not query.strip() or top_k < 1:
            return []
        scored = sorted(
            enumerate(self._index.get_scores(tokenize(query))),
            key=lambda item: item[1], reverse=True,
        )[:top_k]
        results = []
        for rank, (position, score) in enumerate(scored, start=1):
            if score <= 0:
                continue
            chunk = dict(self._chunks[position])
            chunk.update({"id": chunk["chunk_id"], "bm25_score": float(score), "bm25_rank": rank})
            results.append(chunk)
        return results
