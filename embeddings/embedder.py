"""Lazy SentenceTransformers embeddings with normalized vectors for cosine search."""

from __future__ import annotations

import numpy as np


class Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None

    def load(self):
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
        return self.model

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return float32, L2-normalized vectors in the exact input order."""
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        vectors = self.load().encode(
            texts, normalize_embeddings=True, convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)
