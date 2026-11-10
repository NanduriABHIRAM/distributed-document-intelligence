"""Minimal synchronous client for the local Ollama chat API."""

from __future__ import annotations

import os

import httpx


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: float = 90.0):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:latest")
        self.timeout = timeout

    def is_available(self) -> bool:
        """Fast health probe so unavailable local models never block a query."""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=min(self.timeout, 2.0))
            return response.is_success
        except httpx.HTTPError:
            return False

    def model_available(self) -> bool:
        """Check the configured model name without loading it into memory."""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=min(self.timeout, 2.0))
            models = response.json().get("models", []) if response.is_success else []
            return self.model in {model.get("name") for model in models}
        except httpx.HTTPError:
            return False

    def chat(self, system: str, user: str) -> str:
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "think": False,
                "options": {"temperature": 0.1},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "").strip()
        if not content:
            raise RuntimeError("Ollama returned an empty assistant response.")
        return content
