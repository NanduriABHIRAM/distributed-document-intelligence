"""Reproducible throughput and scaling calculations for batch runs."""

from __future__ import annotations


def run_metrics(items_processed: int, elapsed_seconds: float, workers: int = 1, memory_mb: float | None = None) -> dict:
    if elapsed_seconds <= 0 or workers < 1:
        raise ValueError("elapsed_seconds must be positive and workers must be at least one")
    return {"items_processed": items_processed, "elapsed_seconds": elapsed_seconds, "workers": workers, "throughput_per_second": items_processed / elapsed_seconds, "memory_mb": memory_mb}


def scaling_efficiency(single_worker_seconds: float, parallel_seconds: float, workers: int) -> float:
    if min(single_worker_seconds, parallel_seconds) <= 0 or workers < 1:
        raise ValueError("durations must be positive and workers must be at least one")
    return single_worker_seconds / (parallel_seconds * workers)
