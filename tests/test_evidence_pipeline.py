import spacy

from evidence.evidence_validator import validate_claims, validate_entities, validate_relationships
from evidence.entity_extractor import extract_entities
from evidence.relationship_extractor import extract_relationships


def _chunk(text: str) -> dict:
    return {"document_id": "document", "chunk_id": "chunk", "source_path": "sample.txt", "text": text, "location_type": "page", "location_number": 1}


def test_explicit_relationship_is_provenance_preserving():
    nlp = spacy.load("en_core_web_sm")
    chunk = _chunk("Microsoft acquired LinkedIn in 2016.")
    entities = validate_entities(chunk, extract_entities(chunk, nlp))
    relationships = validate_relationships(chunk, extract_relationships(chunk, entities, nlp), entities)
    assert len(relationships) == 1
    relationship = relationships[0]
    assert relationship.relationship_type == "ACQUIRE"
    assert relationship.validation_status == "VALID"
    assert relationship.source.source_text[relationship.source.start_offset:relationship.source.end_offset] == chunk["text"]


def test_invalid_claim_offsets_are_rejected():
    from evidence.schemas import EvidenceClaim, SourceReference
    chunk = _chunk("Ada wrote the report.")
    claim = EvidenceClaim("c", "Ada wrote the report.", "Ada", "write", "report", SourceReference("document", "chunk", "sample.txt", chunk["text"], start_offset=0, end_offset=999), "test")
    assert validate_claims(chunk, [claim])[0].validation_status == "INVALID"
