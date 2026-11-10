"""Structural and provenance validation for extracted evidence candidates."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from evidence.schemas import EvidenceClaim, EvidenceEntity, EvidenceEvent, EvidenceRelationship


class HasSource(Protocol):
    source: object


def _source_is_valid(record: HasSource, chunk: dict) -> bool:
    source = record.source
    if source.document_id != chunk.get("document_id") or source.chunk_id != chunk.get("chunk_id"):
        return False
    if source.source_path != chunk.get("source_path") or source.source_text != chunk.get("text"):
        return False
    start, end = source.start_offset, source.end_offset
    return (type(start) is int and type(end) is int and 0 <= start < end <= len(chunk["text"])
            and source.location_type == chunk.get("location_type")
            and source.location_number == chunk.get("location_number"))


def _set_status(record, valid: bool):
    """Dataclasses are mutable today; replace keeps this safe if that changes."""
    if hasattr(record, "validation_status"):
        return replace(record, validation_status="VALID" if valid else "INVALID")
    return record


def validate_entities(chunk: dict, entities: list[EvidenceEntity]) -> list[EvidenceEntity]:
    validated: list[EvidenceEntity] = []
    for entity in entities:
        valid = _source_is_valid(entity, chunk)
        if valid:
            source = entity.source
            valid = chunk["text"][source.start_offset:source.end_offset] == entity.text
        validated.append(_set_status(entity, valid))
    return validated


def validate_claims(chunk: dict, claims: list[EvidenceClaim], doc=None) -> list[EvidenceClaim]:
    validated = []
    for claim in claims:
        valid = _source_is_valid(claim, chunk)
        if valid:
            source = claim.source
            valid = claim.claim_text == chunk["text"][source.start_offset:source.end_offset].strip()
        status = 'INVALID' if not valid else 'NEEDS_REVIEW'
        if valid and doc is not None:
            from evidence.claim_extractor import extract_claims
            supported = any((c.claim_text,c.subject,c.predicate,c.object) == (claim.claim_text,claim.subject,claim.predicate,claim.object)
                            for c in extract_claims(chunk,None,doc))
            status = 'VALID' if supported else 'INVALID'
        validated.append(replace(claim, validation_status=status))
    return validated


def validate_events(chunk: dict, events: list[EvidenceEvent], doc=None) -> list[EvidenceEvent]:
    validated = []
    for event in events:
        if not _source_is_valid(event, chunk):
            validated.append(_set_status(event, False))
            continue
        span = chunk['text'][event.source.start_offset:event.source.end_offset]
        valid = (event.date_is_explicit == (event.event_date is not None) and
                 all(value is None or value in span for value in (event.actor, event.object, event.event_date)))
        status = 'NEEDS_REVIEW'
        if not valid:
            status = 'INVALID'
        elif doc is not None:
            supported = any(s.start_char == event.source.start_offset and s.end_char == event.source.end_offset
                            and s.root.lemma_ == event.action for s in doc.sents)
            status = 'VALID' if supported and not event.negated and not event.modality else 'NEEDS_REVIEW'
        validated.append(replace(event, validation_status=status))
    return validated


def validate_relationships(chunk, relationships, entities, nlp=None, doc=None):
    # Recheck dependency support, never trust is_explicit supplied by a producer.
    from evidence.relationship_extractor import extract_relationships
    valid_entities = [e for e in validate_entities(chunk, entities) if e.validation_status == 'VALID']
    ids = {e.entity_id for e in valid_entities}
    supported = None
    if doc is not None or nlp is not None:
        supported = {(r.source_entity_id, r.target_entity_id, r.relationship_type,
                      r.source.start_offset, r.source.end_offset)
                     for r in extract_relationships(chunk, valid_entities, nlp, doc)}
    result = []
    for r in relationships:
        valid = (_source_is_valid(r, chunk) and r.is_explicit and r.source_entity_id in ids
                 and r.target_entity_id in ids and r.source_entity_id != r.target_entity_id)
        key = (r.source_entity_id, r.target_entity_id, r.relationship_type, r.source.start_offset, r.source.end_offset)
        status = 'INVALID' if not valid else ('NEEDS_REVIEW' if supported is None else ('VALID' if key in supported else 'INVALID'))
        result.append(replace(r, validation_status=status))
    return result
