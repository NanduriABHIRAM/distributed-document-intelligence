"""Small, explicit temporal compatibility checks for evidence candidates."""

from __future__ import annotations

from datetime import date
import re


def _year(value: object) -> int | None:
    match = re.search(r"\b(19|20)\d{2}\b", str(value or ""))
    return int(match.group()) if match else None


def compare_temporal_claims(claim_a: dict, claim_b: dict) -> dict:
    """Classify time compatibility; unknown dates never imply contradiction."""
    left = _year(claim_a.get("valid_from") or claim_a.get("event_date") or claim_a.get("claim_text"))
    right = _year(claim_b.get("valid_from") or claim_b.get("event_date") or claim_b.get("claim_text"))
    if left is None or right is None:
        return {"relationship": "unknown", "reason": "One or both claims have no explicit valid time."}
    if left == right:
        return {"relationship": "same_period", "reason": f"Both claims refer to {left}."}
    return {"relationship": "historical_update", "reason": f"Claims refer to different explicit years: {left} and {right}.", "years": [left, right]}
