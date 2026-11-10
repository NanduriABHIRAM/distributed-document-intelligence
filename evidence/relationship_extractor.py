"""Extract only explicit, sentence-level relationships between known entities.

This baseline deliberately requires a dependency path from a subject entity to an
object entity.  Sharing a chunk or a sentence is never enough to create an edge.
"""

from __future__ import annotations

import hashlib
from evidence.qualifiers import qualifiers
from typing import Iterable

from evidence.schemas import EvidenceEntity, EvidenceRelationship, SourceReference


_SUBJECT_DEPS = {"nsubj", "nsubjpass", "csubj", "csubjpass"}
_OBJECT_DEPS = {"dobj", "obj", "attr", "oprd", "pobj"}


def generate_relationship_id(
    document_id: str, chunk_id: str, source_entity_id: str,
    target_entity_id: str, relationship_type: str, start: int, end: int,
) -> str:
    raw = f"{document_id}:{chunk_id}:{source_entity_id}:{target_entity_id}:{relationship_type}:{start}:{end}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _normalise_relation(token) -> str:
    """Return a stable, readable edge label from an explicit predicate."""
    value = (getattr(token, "lemma_", "") or getattr(token, "text", "")).strip()
    return "_".join(value.upper().split()) or "RELATED_TO"


def _entity_for_token(token, entities: Iterable[EvidenceEntity]) -> EvidenceEntity | None:
    start = getattr(token, "idx", -1)
    end = start + len(getattr(token, "text", ""))
    for entity in entities:
        source = entity.source
        if source.start_offset is not None and source.end_offset is not None:
            if source.start_offset <= start and end <= source.end_offset:
                return entity
    return None


def _entity_for_subtree(token, entities: Iterable[EvidenceEntity]) -> EvidenceEntity | None:
    direct = _entity_for_token(token, entities)
    if direct:
        return direct
    # Do not mistake a possessor or relative-clause entity for the argument itself.
    found = {_entity_for_token(child, entities).entity_id: _entity_for_token(child, entities)
             for child in getattr(token, 'children', ())
             if getattr(child, 'dep_', '') in {'compound', 'flat', 'name'} and _entity_for_token(child, entities)}
    return next(iter(found.values())) if len(found) == 1 else None



def extract_relationships(
    chunk: dict, entities: list[EvidenceEntity], nlp, doc=None,
) -> list[EvidenceRelationship]:
    """Return explicit entity-to-entity relations supported by one sentence.

    ``entities`` must have been extracted from the same chunk.  This preserves
    deterministic IDs and makes validation independent of model output.
    """
    if not entities:
        return []

    doc = doc if doc is not None else nlp(chunk["text"])
    relationships: list[EvidenceRelationship] = []
    seen: set[tuple[str, str, str, int, int]] = set()

    for sentence in doc.sents:
        q = qualifiers(sentence.text)
        if q["negated"] or q["modality"] or q["attribution"]:
            continue
        verbs = [token for token in sentence if getattr(token, "pos_", "") in {"VERB", "AUX"}]
        for predicate in verbs:
            subjects = [
                _entity_for_subtree(token, entities)
                for token in getattr(predicate, "children", ())
                if getattr(token, "dep_", "") in _SUBJECT_DEPS
            ]
            objects = [
                _entity_for_subtree(token, entities)
                for token in getattr(predicate, "children", ())
                if getattr(token, "dep_", "") in _OBJECT_DEPS
            ]
            subjects = [entity for entity in subjects if entity]
            objects = [entity for entity in objects if entity]
            if not subjects or not objects:
                continue

            relation_type = _normalise_relation(predicate)
            for source_entity in subjects:
                for target_entity in objects:
                    if source_entity.entity_id == target_entity.entity_id:
                        continue
                    key = (source_entity.entity_id, target_entity.entity_id, relation_type,
                           sentence.start_char, sentence.end_char)
                    if key in seen:
                        continue
                    seen.add(key)
                    start, end = sentence.start_char, sentence.end_char
                    source = SourceReference(
                        document_id=chunk["document_id"], chunk_id=chunk["chunk_id"],
                        source_path=chunk["source_path"], source_text=chunk["text"],
                        location_type=chunk.get("location_type"),
                        location_number=chunk.get("location_number"),
                        start_offset=start, end_offset=end,
                    )
                    relationships.append(EvidenceRelationship(
                        relationship_id=generate_relationship_id(
                            chunk["document_id"], chunk["chunk_id"], source_entity.entity_id,
                            target_entity.entity_id, relation_type, start, end,
                        ),
                        source_entity_id=source_entity.entity_id,
                        target_entity_id=target_entity.entity_id,
                        relationship_type=relation_type,
                        source=source,
                        is_explicit=True,
                    ))
    return relationships
