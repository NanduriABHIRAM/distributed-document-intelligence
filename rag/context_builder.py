"""Build compact, source-labelled context for grounded answer generation."""

from __future__ import annotations


def build_evidence_context(results: list[dict]) -> str:
    parts = []
    for position, result in enumerate(results, start=1):
        location = result.get("location_number")
        location_label = f"{result.get('location_type', 'section')} {location}" if location else "source excerpt"
        parts.append(
            f"[E{position}] {result.get('document_id', 'Unknown document')} — {location_label}\n"
            f"{result.get('text', '').strip()}"
        )
    return "\n\n".join(parts)
