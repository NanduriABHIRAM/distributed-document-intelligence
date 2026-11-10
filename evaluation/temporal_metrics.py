"""Metrics for labelled temporal relation experiments."""

from __future__ import annotations


def temporal_accuracy(predicted: list[str], expected: list[str]) -> float:
    if len(predicted) != len(expected):
        raise ValueError("predicted and expected must have equal length")
    return sum(left == right for left, right in zip(predicted, expected)) / len(expected) if expected else 0.0


def temporal_report(predicted: list[str], expected: list[str]) -> dict:
    labels = sorted(set(predicted) | set(expected))
    return {
        "samples": len(expected), "accuracy": temporal_accuracy(predicted, expected),
        "per_label_recall": {label: (sum(p == e == label for p, e in zip(predicted, expected)) / max(1, expected.count(label))) for label in labels},
    }
