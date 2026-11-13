"""Synchronous client for the local Ollama chat API with actionable failures."""

from __future__ import annotations

import os
import re
import httpx

from configs.runtime import option, settings


class OllamaError(RuntimeError):
    category = "model_error"


class OllamaConnectionError(OllamaError):
    category = "connection_error"


class OllamaTimeoutError(OllamaError):
    category = "timeout"


class OllamaResponseError(OllamaError):
    category = "model_error"


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: float = 90.0):
        settings()
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or option("models", "generation", "qwen3:4b", "OLLAMA_MODEL")
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            return httpx.get(f"{self.base_url}/api/tags", timeout=min(self.timeout, 2.0)).is_success
        except httpx.HTTPError:
            return False

    def model_available(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=min(self.timeout, 2.0))
            models = response.json().get("models", []) if response.is_success else []
            return self.model in {item.get("name") for item in models}
        except httpx.HTTPError:
            return False

    def chat(self, system: str, user: str) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "stream": False, "think": False,
                      "options": {"temperature": 0.1},
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise OllamaTimeoutError("Ollama generation timed out.") from error
        except httpx.ConnectError as error:
            raise OllamaConnectionError("Ollama could not be reached.") from error
        except httpx.HTTPError as error:
            raise OllamaResponseError("Ollama rejected the generation request.") from error
        try:
            content = response.json().get("message", {}).get("content", "").strip()
        except (ValueError, AttributeError) as error:
            raise OllamaResponseError("Ollama returned an invalid response.") from error
        # Older Ollama/Qwen combinations can place the reasoning trace in
        # content even with ``think: false``. Some versions omit the opening
        # tag but still emit ``</think>``. A closed terminator is protocol
        # metadata, so retain only the final-answer suffix after it; do not
        # remove arbitrary prose when no terminator exists.
        if "</think>" in content:
            content = content.rsplit("</think>", 1)[1].strip()
        else:
            content = re.sub(r"^\s*<think>.*?</think>\s*", "", content, flags=re.DOTALL).strip()
        if not content:
            raise OllamaResponseError("Ollama returned an empty assistant response.")
        return content
