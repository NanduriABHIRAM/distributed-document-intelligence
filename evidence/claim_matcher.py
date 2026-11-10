"""High-precision candidate pairing before temporal or contradiction analysis."""

from __future__ import annotations

import re


def _tokens(value: object) -> set[str]:
    return set(re.findall(r"\w+", str(value or "").casefold()))


def find_candidate_claim_pairs(claims: list[dict], similarity_threshold: float = 0.80) -> list[tuple[str, str]]:
    pairs = []
    for index, left in enumerate(claims):
        for right in claims[index + 1:]:
            if left.get("subject", "").casefold() != right.get("subject", "").casefold():
                continue
            if left.get("predicate", "").casefold() != right.get("predicate", "").casefold():
                continue
            left_tokens, right_tokens = _tokens(left.get("claim_text")), _tokens(right.get("claim_text"))
            similarity = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
            if similarity >= similarity_threshold:
                pairs.append((left["claim_id"], right["claim_id"]))
    return pairs
