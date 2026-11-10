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
    return start is not None and end is not None and 0 <= start < end <= len(chunk["text"])


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


def validate_claims(chunk: dict, claims: list[EvidenceClaim]) -> list[EvidenceClaim]:
    validated = []
    for claim in claims:
        valid = _source_is_valid(claim, chunk)
        if valid:
            source = claim.source
            valid = claim.claim_text in chunk["text"][source.start_offset:source.end_offset]
        validated.append(_set_status(claim, valid))
    return validated


def validate_events(chunk: dict, events: list[EvidenceEvent]) -> list[EvidenceEvent]:
    return [_set_status(event, _source_is_valid(event, chunk)) for event in events]


def validate_relationships(
    chunk: dict, relationships: list[EvidenceRelationship], entities: list[EvidenceEntity],
) -> list[EvidenceRelationship]:
    entity_ids = {entity.entity_id for entity in entities}
    validated = []
    for relationship in relationships:
        valid = (
            _source_is_valid(relationship, chunk)
            and relationship.is_explicit
            and relationship.source_entity_id in entity_ids
            and relationship.target_entity_id in entity_ids
            and relationship.source_entity_id != relationship.target_entity_id
        )
        validated.append(_set_status(relationship, valid))
    return validated
