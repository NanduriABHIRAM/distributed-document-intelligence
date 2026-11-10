"""Safe baseline answer generation before a locally configured LLM is introduced."""

from __future__ import annotations


def generate_answer(query: str, evidence_context: str, evidence_count: int = 0) -> dict:
    """Return a transparent extractive response, never an unsupported synthesis.

    Ollama-based synthesis can replace this later, but this response is useful now
    because every displayed statement is a verbatim retrieved excerpt.
    """
    if not evidence_context:
        return {
            "answer": "I could not find supporting evidence in the indexed documents.",
            "grounded": True,
            "mode": "insufficient_evidence",
        }
    return {
        "answer": f"Found {evidence_count} relevant evidence excerpt(s). Review the cited source passages below; no unsupported synthesis was generated.",
        "grounded": True,
        "mode": "extractive_baseline",
    }
