from dataclasses import dataclass
from typing import Optional


@dataclass
class SourceReference:
    document_id: str
    chunk_id: str
    source_path: str
    source_text: str

    location_type: Optional[str] = None
    location_number: Optional[int] = None

    start_offset: Optional[int] = None
    end_offset: Optional[int] = None


@dataclass
class EvidenceEntity:
    entity_id: str
    text: str
    normalized_text: str
    entity_type: str
    source: SourceReference

    extraction_method: str
    confidence: Optional[float] = None
    validation_status: str = "PENDING"


@dataclass
class EvidenceClaim:
    claim_id: str
    claim_text: str

    subject: Optional[str]
    predicate: Optional[str]
    object: Optional[str]

    source: SourceReference
    extraction_method: str
    validation_status: str = "PENDING"


@dataclass
class EvidenceEvent:
    event_id: str
    event_type: str

    action: str
    actor: Optional[str]
    object: Optional[str]

    event_date: Optional[str]
    date_is_explicit: bool

    source: SourceReference
    extraction_method: str = "rule_based_event_extractor"
    validation_status: str = "PENDING"


@dataclass
class EvidenceRelationship:
    relationship_id: str

    source_entity_id: str
    target_entity_id: str

    relationship_type: str

    source: SourceReference
    is_explicit: bool

    validation_status: str = "PENDING"
