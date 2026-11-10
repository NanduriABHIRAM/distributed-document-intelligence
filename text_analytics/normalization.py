"""Safe, lightweight normalization used for matching—not source replacement."""

from __future__ import annotations

import re


def normalize_claim(claim: dict) -> dict:
    result = dict(claim)
    for key in ("subject", "predicate", "object"):
        if result.get(key) is not None:
            result[f"normalized_{key}"] = " ".join(str(result[key]).casefold().split())
    text = str(result.get("claim_text", ""))
    years = re.findall(r"\b(?:19|20)\d{2}\b", text)
    if years:
        result["explicit_years"] = years
    quantities = re.findall(r"\b\d+(?:\.\d+)?\s*(?:%|percent|users?|employees?|ms|gb|mb)?\b", text, flags=re.I)
    if quantities:
        result["quantities"] = quantities
    return result
