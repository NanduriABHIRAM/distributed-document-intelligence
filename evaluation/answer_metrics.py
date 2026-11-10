"""Metrics for human- or programmatically-labelled grounded answers."""

from __future__ import annotations


def citation_precision(cited_ids: set[str], supported_ids: set[str]) -> float:
    return len(cited_ids & supported_ids) / len(cited_ids) if cited_ids else 0.0


def citation_completeness(supported_ids: set[str], required_ids: set[str]) -> float:
    return len(supported_ids & required_ids) / len(required_ids) if required_ids else 1.0


def groundedness_rate(labels: list[bool]) -> float:
    return sum(labels) / len(labels) if labels else 0.0
