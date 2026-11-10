"""Bundle evidence extracted from a chunk without discarding provenance."""

from __future__ import annotations

from dataclasses import dataclass, field

from evidence.schemas import EvidenceClaim, EvidenceEntity, EvidenceEvent, EvidenceRelationship


@dataclass
class ChunkEvidence:
    chunk_id: str
    entities: list[EvidenceEntity] = field(default_factory=list)
    claims: list[EvidenceClaim] = field(default_factory=list)
    events: list[EvidenceEvent] = field(default_factory=list)
    relationships: list[EvidenceRelationship] = field(default_factory=list)


def build_evidence(
    chunk: dict,
    entities: list[EvidenceEntity],
    claims: list[EvidenceClaim],
    events: list[EvidenceEvent],
    relationships: list[EvidenceRelationship],
) -> ChunkEvidence:
    """Create one consistent evidence bundle and reject cross-chunk mixing early."""
    records = [*entities, *claims, *events, *relationships]
    mismatched = [record for record in records if record.source.chunk_id != chunk["chunk_id"]]
    if mismatched:
        raise ValueError("Cannot build evidence bundle from records belonging to another chunk.")
    return ChunkEvidence(
        chunk_id=chunk["chunk_id"], entities=entities, claims=claims,
        events=events, relationships=relationships,
    )
