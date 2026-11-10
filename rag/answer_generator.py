"""Grounded answer generation with citation validation and safe local fallback."""

from __future__ import annotations

import httpx

from rag.citation_validator import validate_citations
from rag.ollama_client import OllamaClient


_SYSTEM_PROMPT = """You are TraceRAG, a careful teaching assistant.
Answer the student's question using only the supplied evidence. Explain ideas clearly
for a student. Put one or more citations in the form [E1] directly after every factual
statement. Do not invent citations. If the evidence is incomplete, say exactly what it
does not establish. Never use information outside the evidence."""


def _fallback(evidence_count: int, reason: str | None = None) -> dict:
    message = f"Found {evidence_count} relevant evidence excerpt(s). Review the cited source passages below; no unsupported synthesis was generated."
    if reason:
        message += f" ({reason})"
    return {"answer": message, "grounded": True, "mode": "extractive_fallback", "citation_validation": {"valid": True, "citations": [], "errors": []}}


def generate_answer(query: str, evidence_context: str, evidence_count: int = 0, client: OllamaClient | None = None) -> dict:
    """Generate a cited student answer, rejecting unsafe local-model output."""
    if not evidence_context:
        return {
            "answer": "I could not find supporting evidence in the indexed documents.",
            "grounded": True,
            "mode": "insufficient_evidence",
            "citation_validation": {"valid": True, "citations": [], "errors": []},
        }
    allowed = {f"E{number}" for number in range(1, evidence_count + 1)}
    try:
        active_client = client or OllamaClient()
        if client is None and not active_client.is_available():
            return _fallback(evidence_count, "Local Ollama is unavailable; showing source evidence instead")
        answer = active_client.chat(_SYSTEM_PROMPT, f"Question: {query}\n\nEvidence:\n{evidence_context}")
        validation = validate_citations(answer, allowed)
        if validation["valid"] and validation["citations"]:
            return {"answer": answer, "grounded": True, "mode": "ollama_grounded", "citation_validation": validation}
        return _fallback(evidence_count, "The local model response did not satisfy the citation policy")
    except (httpx.HTTPError, RuntimeError, OSError) as error:
        return _fallback(evidence_count, "Local Ollama is unavailable; showing source evidence instead")
