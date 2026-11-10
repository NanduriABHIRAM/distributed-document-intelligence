import spacy
from configs.runtime import option
import hashlib

from evidence.schemas import EvidenceEntity,SourceReference

def load_nlp():
    return spacy.load(option("models", "spacy", "en_core_web_sm", "SPACY_MODEL"))

def normalize_entity(text:str) -> str:
    return " ".join(text.strip().casefold().split())

def map_entity_type(label: str) -> str:

    entity_types = {
        "PERSON": "PERSON",
        "ORG": "ORGANIZATION",
        "GPE": "LOCATION",
        "LOC": "LOCATION",
        "FAC": "LOCATION",
        "DATE": "DATE",
        "TIME": "TIME",
        "PRODUCT": "PRODUCT",
        "EVENT": "EVENT",
        "WORK_OF_ART": "WORK_OF_ART",
        "LAW": "LAW",
        "LANGUAGE": "LANGUAGE",
        "NORP": "GROUP"
    }

    return entity_types.get(label, "OTHER")


def generate_entity_id(
    document_id: str,
    chunk_id: str,
    start: int,
    end: int,
    entity_type: str
) -> str:

    raw_id = f"{document_id}:{chunk_id}:{start}:{end}:{entity_type}"

    return hashlib.sha256(
        raw_id.encode("utf-8")
    ).hexdigest()[:16]



def extract_entities(chunk: dict, nlp, doc=None) -> list[EvidenceEntity]:

    text = chunk["text"]

    doc = doc if doc is not None else nlp(text)

    entities = []

    for ent in doc.ents:

        raw_entity_text = ent.text
        entity_text = raw_entity_text.strip()

        if not entity_text:
            continue

        entity_type = map_entity_type(ent.label_)

        normalized_text = normalize_entity(entity_text)

        # spaCy may include a newline in an entity span.  Once we trim displayed
        # text, trim the provenance offsets too so the span remains verifiable.
        leading_whitespace = len(raw_entity_text) - len(raw_entity_text.lstrip())
        trailing_whitespace = len(raw_entity_text) - len(raw_entity_text.rstrip())
        start = ent.start_char + leading_whitespace
        end = ent.end_char - trailing_whitespace

        entity_id = generate_entity_id(
            document_id=chunk["document_id"],
            chunk_id=chunk["chunk_id"],
            start=start,
            end=end,
            entity_type=entity_type
        )

        source = SourceReference(
            document_id=chunk["document_id"],
            chunk_id=chunk["chunk_id"],
            source_path=chunk["source_path"],
            source_text=text,
            location_type=chunk.get("location_type"),
            location_number=chunk.get("location_number"),
            start_offset=start,
            end_offset=end
        )

        evidence_entity = EvidenceEntity(
            entity_id=entity_id,
            text=entity_text,
            normalized_text=normalized_text,
            entity_type=entity_type,
            source=source,
            extraction_method="spacy_ner"
        )

        entities.append(evidence_entity)

    return entities
