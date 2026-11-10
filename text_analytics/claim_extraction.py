from dataclasses import dataclass
from typing import Any

@dataclass
class Claim:
    claim_id: str
    text: str
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    recorded_at: str | None = None
    source_document_id: str | None = None
    source_chunk_id: str | None = None
    confidence: float | None = None

def extract_claims(text: str, metadata: dict[str, Any] | None = None) -> list[Claim]:
    from text_analytics.ner import _nlp
    import hashlib
    metadata = metadata or {}
    claims = []
    for sentence in _nlp()(text).sents:
        subject = next((token.text for token in sentence if token.dep_ in {"nsubj", "nsubjpass", "csubj"}), None)
        if subject is None or sentence.root.pos_ not in {"VERB", "AUX"}:
            continue
        object_text = next((token.text for token in sentence if token.dep_ in {"obj", "dobj", "attr", "oprd"}), None)
        raw = f"{metadata.get('source_chunk_id', '')}:{sentence.start_char}:{sentence.end_char}"
        claims.append(Claim(
            claim_id=hashlib.sha256(raw.encode()).hexdigest()[:16], text=sentence.text.strip(),
            subject=subject, predicate=sentence.root.lemma_, object=object_text,
            source_document_id=metadata.get("source_document_id"), source_chunk_id=metadata.get("source_chunk_id"),
        ))
    return claims
