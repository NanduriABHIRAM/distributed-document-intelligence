"""Citation integrity and conservative source-support checks.

Citation identity, provenance, exact quotations, and semantic support are kept
separate: no paraphrase is presented as semantically verified without an NLI model.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

_CITATION = re.compile(r"\[([A-Za-z]\w*)\]")
_CITATION_GROUP = re.compile(r"(?:\s*\[[A-Za-z]\w*\])+")
_SENTENCES = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-z0-9]+")
_STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "were", "with"}
_NEGATIONS = {"no", "not", "never", "none", "without", "cannot", "cant", "didnt", "doesnt", "wont"}


def _normalise(value: str) -> str:
    return " ".join(value.strip().strip('"“”').split()).casefold()


def _stem(value: str) -> str:
    if len(value) > 5 and value.endswith("ing"):
        return value[:-3]
    if len(value) > 4 and value.endswith("ed"):
        return value[:-2] + ("e" if not value.endswith("eed") else "")
    if len(value) > 3 and value.endswith("s"):
        return value[:-1]
    return value


def _words(value: str) -> set[str]:
    return {_stem(word.casefold()) for word in _WORD.findall(value) if word.casefold() not in _STOP}


def _provenance(source: dict) -> tuple[str, str | None]:
    reference = str(source.get("source_path") or "").strip()
    if not reference:
        return "MISSING", "source document is missing."
    parsed = urlparse(reference)
    if (parsed.scheme and parsed.scheme != "file") or reference.startswith("urn:"):
        return "REMOTE_NOT_CHECKED", None
    path = Path(reference)
    if not path.is_file():
        return "MISSING", "source file is missing."
    expected_hash = source.get("metadata", {}).get("sha256")
    if expected_hash:
        from ingestion.utils import sha256_file
        if sha256_file(path) != expected_hash:
            return "CHANGED", "source file changed since ingestion."
    return "VERIFIED", None


def _support(statement: str, source_text: str) -> str:
    normalized = _normalise(statement)
    sentences = [_normalise(value) for value in _SENTENCES.split(source_text) if value.strip()]
    if normalized == _normalise(source_text) or normalized in sentences:
        return "VERIFIED_EXACT"
    statement_words, source_words = _words(statement), _words(source_text)
    overlap = statement_words & source_words
    if overlap and bool(statement_words & _NEGATIONS) != bool(source_words & _NEGATIONS):
        return "UNSUPPORTED"
    # This only establishes that the citation plausibly refers to the excerpt.
    # It is not semantic entailment verification.
    needed = 1 if min(len(statement_words), len(source_words)) <= 2 else 2
    return "CITATION_VALID_UNVERIFIED" if len(overlap) >= needed else "UNSUPPORTED"


def validate_citations(answer: str, allowed_source_ids: set[str], evidence=None) -> dict:
    """Return explicit status for exact quotations versus unverified paraphrases."""
    citations = sorted(set(_CITATION.findall(answer)))
    errors, warnings, claims = [], [], []
    errors.extend(f"Unknown citation: {value}" for value in sorted(set(citations) - allowed_source_ids))
    if not citations:
        errors.append("The generated answer contains no evidence citations.")
    sources: dict[str, dict] = {}
    if evidence is None:
        errors.append("Source evidence is required to verify support.")
    else:
        for item in evidence:
            evidence_id = item.get("evidence_id")
            if not evidence_id:
                continue
            if evidence_id in sources:
                errors.append(f"Duplicate retrieved evidence ID: {evidence_id}.")
            else:
                sources[evidence_id] = item

    cursor = 0
    for match in _CITATION_GROUP.finditer(answer):
        statement = answer[cursor:match.start()].strip().strip('"“”')
        identifiers = _CITATION.findall(match.group())
        claim = {"statement": statement, "citations": identifiers, "exact_source_match": False,
                 "semantic_support": "NOT_VERIFIED", "support_status": "UNSUPPORTED", "provenance": {}}
        if not statement:
            errors.append("Citation has no attached statement.")
        statuses = []
        for identifier in identifiers:
            source = sources.get(identifier)
            if source is None:
                errors.append(f"{identifier} was not retrieved.")
                claim["provenance"][identifier] = "MISSING_EVIDENCE"
                continue
            provenance, problem = _provenance(source)
            claim["provenance"][identifier] = provenance
            if problem:
                errors.append(f"{identifier} {problem}")
                continue
            source_text = str(source.get("text") or "").strip()
            if not source_text:
                errors.append(f"{identifier} has no attached source text.")
                continue
            statuses.append(_support(statement, source_text) if statement else "UNSUPPORTED")
        if statuses:
            if "VERIFIED_EXACT" in statuses:
                claim["exact_source_match"], claim["support_status"] = True, "VERIFIED_EXACT"
            elif "CITATION_VALID_UNVERIFIED" in statuses:
                claim["support_status"] = "CITATION_VALID_UNVERIFIED"
                warnings.append("A paraphrased claim has not undergone semantic entailment verification.")
            else:
                errors.append("A citation does not support its attached statement.")
        claims.append(claim)
        cursor = match.end()
    if answer[cursor:].strip():
        errors.append("Answer contains uncited trailing text.")

    valid = not errors and bool(citations) and bool(claims)
    if not valid:
        status = "UNSUPPORTED"
    elif all(claim["support_status"] == "VERIFIED_EXACT" for claim in claims):
        status = "VERIFIED_EXACT"
    else:
        status = "CITATION_VALID_UNVERIFIED"
    return {"valid": valid, "citation_valid": valid, "citations": citations, "errors": errors,
            "warnings": sorted(set(warnings)), "claims": claims, "answer_status": status,
            "method": "exact_source_sentence_with_unverified_paraphrase",
            "semantic_entailment_verified": False}
