"""Ollama embedding client used by the optional dense retrieval index."""

from __future__ import annotations

import os

import httpx
import numpy as np


class OllamaEmbedder:
    def __init__(self, model: str | None = None, base_url: str | None = None, timeout: float = 120.0):
        self.model = model or os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = timeout

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        response = httpx.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model, "input": texts}, timeout=self.timeout,
        )
        # Long textbook chunks can make a large batch exceed Ollama's request
        # limit. Split only the rejected request, retaining efficient batches
        # for the rest of the corpus and preserving input order.
        if response.status_code == 400 and len(texts) > 1:
            midpoint = len(texts) // 2
            return np.vstack((self.encode(texts[:midpoint]), self.encode(texts[midpoint:])))
        response.raise_for_status()
        vectors = np.asarray(response.json().get("embeddings", []), dtype=np.float32)
        if vectors.ndim != 2 or len(vectors) != len(texts):
            raise RuntimeError("Ollama returned an invalid embedding response.")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.maximum(norms, 1e-12)
