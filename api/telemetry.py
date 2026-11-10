"""Small in-process operational telemetry; never substitutes for research metrics."""

from __future__ import annotations

from threading import Lock


class RetrievalTelemetry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests = 0
        self._total_latency_ms = 0.0

    def record(self, latency_ms: float) -> None:
        with self._lock:
            self._requests += 1
            self._total_latency_ms += latency_ms

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "requests": self._requests,
                "average_retrieval_latency_ms": round(self._total_latency_ms / self._requests, 2) if self._requests else None,
            }


retrieval_telemetry = RetrievalTelemetry()
