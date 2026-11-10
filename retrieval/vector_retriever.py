"""FAISS-backed dense retrieval with an explicit vector-position to chunk mapping."""

from __future__ import annotations

import numpy as np
import json
from pathlib import Path
import os
from datetime import datetime, timezone


class VectorRetriever:
    def __init__(self, index=None, embedder=None):
        self.index = index
        self.embedder = embedder
        self.records: list[dict] = []

    def fit(self, chunks: list[dict]) -> None:
        if self.embedder is None:
            raise ValueError("VectorRetriever requires an embedder before fitting.")
        self.index, self.records = None, []
        self.add(chunks)

    def add(self, chunks: list[dict]) -> None:
        """Embed and append one bounded batch without losing vector alignment."""
        if self.embedder is None:
            raise ValueError("VectorRetriever requires an embedder before adding chunks.")
        vectors = self.embedder.encode([chunk.get("text", "") for chunk in chunks])
        if not len(vectors):
            return
        import faiss
        if self.index is None:
            self.index = faiss.IndexFlatIP(vectors.shape[1])
        elif self.index.d != vectors.shape[1]:
            raise ValueError("Embedding dimensions do not match the existing FAISS index.")
        self.index.add(vectors)
        self.records.extend(chunks)

    def save(self, index_path: str | Path, records_path: str | Path, metadata: dict | None = None) -> None:
        """Persist the FAISS index and its position-to-chunk mapping together."""
        if self.index is None:
            raise RuntimeError("No vector index is available to save.")
        import faiss
        index_path, records_path = Path(index_path), Path(records_path)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path = records_path.with_suffix(".meta.json")
        index_temp = index_path.with_suffix(index_path.suffix + ".tmp")
        records_temp = records_path.with_suffix(records_path.suffix + ".tmp")
        metadata_temp = metadata_path.with_suffix(metadata_path.suffix + ".tmp")
        faiss.write_index(self.index, str(index_temp))
        records_temp.write_text(json.dumps(self.records, ensure_ascii=False), encoding="utf-8")
        details = {
            "vector_count": len(self.records), "dimensions": self.index.d,
            "created_at": datetime.now(timezone.utc).isoformat(), **(metadata or {}),
        }
        metadata_temp.write_text(json.dumps(details, indent=2), encoding="utf-8")
        os.replace(index_temp, index_path)
        os.replace(records_temp, records_path)
        os.replace(metadata_temp, metadata_path)

    @classmethod
    def load(cls, index_path: str | Path, records_path: str | Path, embedder):
        """Load a persisted index without re-embedding documents."""
        import faiss
        index_path, records_path = Path(index_path), Path(records_path)
        retriever = cls(index=faiss.read_index(str(index_path)), embedder=embedder)
        retriever.records = json.loads(records_path.read_text(encoding="utf-8"))
        if retriever.index.ntotal != len(retriever.records):
            raise RuntimeError("FAISS index and vector record mapping have different lengths.")
        return retriever

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
