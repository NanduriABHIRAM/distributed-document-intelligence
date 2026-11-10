"""Build compact, source-labelled context for grounded answer generation."""

from __future__ import annotations


def curate_evidence(results: list[dict], max_characters: int = 18_000) -> list[dict]:
    """Deduplicate and bound evidence once, before API and model consumption."""
    curated, seen_texts, used = [], set(), 0
    for result in results:
        text = result.get("text", "").strip()
        fingerprint = " ".join(text.casefold().split())
        if not text or fingerprint in seen_texts:
            continue
        seen_texts.add(fingerprint)
        location = result.get("location_number")
        location_label = f"{result.get('location_type', 'section')} {location}" if location else "source excerpt"
        score = result.get("rrf_score", result.get("bm25_score", result.get("vector_score", "n/a")))
        evidence_id = f"E{len(curated) + 1}"
        part = (
            f"[{evidence_id}] document={result.get('document_id', 'Unknown')}; "
            f"chunk={result.get('chunk_id', 'Unknown')}; location={location_label}; score={score}\n"
            f"SOURCE TEXT: {text}"
        )
        if used + len(part) > max_characters:
            break
        item = dict(result)
        item["evidence_id"] = evidence_id
        curated.append(item)
        used += len(part)
    return curated


def build_evidence_context(evidence: list[dict]) -> str:
    """Serialize already-curated evidence, keeping API IDs and prompt IDs equal."""
    parts = []
    for result in evidence:
        location = result.get("location_number")
        location_label = f"{result.get('location_type', 'section')} {location}" if location else "source excerpt"
        score = result.get("rrf_score", result.get("bm25_score", result.get("vector_score", "n/a")))
        parts.append(
            f"[{result['evidence_id']}] document={result.get('document_id', 'Unknown')}; "
            f"chunk={result.get('chunk_id', 'Unknown')}; location={location_label}; score={score}\n"
            f"SOURCE TEXT: {result.get('text', '').strip()}"
        )
    return "\n\n".join(parts)
