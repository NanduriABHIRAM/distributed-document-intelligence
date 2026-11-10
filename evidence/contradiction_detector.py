"""Conservative deterministic contradiction baseline for candidate claim pairs."""

from __future__ import annotations

import re


def classify_claim_pair(claim_a: str, claim_b: str) -> dict:
    left, right = claim_a.casefold().strip(), claim_b.casefold().strip()
    if left == right:
        return {"label": "entails", "entailment": 1.0, "contradiction": 0.0, "neutral": 0.0, "reason": "Identical normalized statements."}
    years_a = set(re.findall(r"\b(?:19|20)\d{2}\b", left))
    years_b = set(re.findall(r"\b(?:19|20)\d{2}\b", right))
    if years_a and years_b and years_a != years_b:
        return {"label": "historical_update", "entailment": 0.0, "contradiction": 0.0, "neutral": 1.0, "reason": "Different explicit years require temporal interpretation."}
    negated_a, negated_b = bool(re.search(r"\b(no|not|never|without)\b", left)), bool(re.search(r"\b(no|not|never|without)\b", right))
    shared = set(re.findall(r"\w+", left)) & set(re.findall(r"\w+", right))
    if shared and negated_a != negated_b:
        return {"label": "contradiction", "entailment": 0.0, "contradiction": 0.8, "neutral": 0.2, "reason": "Shared terms with opposing negation; needs review."}
    return {"label": "neutral", "entailment": 0.0, "contradiction": 0.0, "neutral": 1.0, "reason": "Insufficient deterministic evidence of agreement or conflict."}
