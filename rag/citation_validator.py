"""Validate simple [E1] style citations against retrieved evidence IDs."""

from __future__ import annotations

import re


def validate_citations(answer: str, allowed_source_ids: set[str]) -> dict:
    citations = set(re.findall(r"\[([A-Za-z]\w*)\]", answer))
    invalid = sorted(citation for citation in citations if citation not in allowed_source_ids)
    return {"valid": not invalid, "citations": sorted(citations), "errors": [f"Unknown citation: {item}" for item in invalid]}
