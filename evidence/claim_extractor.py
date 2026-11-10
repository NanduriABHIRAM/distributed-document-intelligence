import hashlib
from evidence.qualifiers import qualifiers
import spacy

from evidence.schemas import EvidenceClaim, SourceReference


def generate_claim_id(
    document_id: str,
    chunk_id: str,
    start: int,
    end: int
) -> str:

    raw_id = f"{document_id}:{chunk_id}:{start}:{end}"

    return hashlib.sha256(
        raw_id.encode("utf-8")
    ).hexdigest()[:16]


def extract_subject(sentence):

    subject_dependencies = {
        "nsubj",
        "nsubjpass",
        "csubj",
        "csubjpass"
    }

    for token in sentence:
        if token.dep_ in subject_dependencies:
            return token.text

    return None


def extract_object(sentence):

    object_dependencies = {
        "dobj",
        "obj",
        "attr",
        "oprd"
    }

    for token in sentence:
        if token.dep_ in object_dependencies:
            return token.text

    return None


def is_candidate_claim(sentence):

    # Remove empty sentences
    if not sentence.text.strip():
        return False

    # Ignore questions
    if sentence.text.strip().endswith("?"):
        return False

    # The main word should normally be a verb
    if sentence.root.pos_ not in {"VERB", "AUX"}:
        return False

    # Require a grammatical subject
    subject = extract_subject(sentence)

    if subject is None:
        return False

    return True


def extract_claims(chunk: dict, nlp, doc=None) -> list[EvidenceClaim]:

    text = chunk["text"]

    doc = doc if doc is not None else nlp(text)

    claims = []

    for sentence in doc.sents:

        if not is_candidate_claim(sentence):
            continue

        subject = extract_subject(sentence)

        predicate = sentence.root.lemma_

        object_text = extract_object(sentence)

        claim_text = sentence.text.strip()

        start = sentence.start_char
        end = sentence.end_char

        claim_id = generate_claim_id(
            document_id=chunk["document_id"],
            chunk_id=chunk["chunk_id"],
            start=start,
            end=end
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

        claim = EvidenceClaim(
            claim_id=claim_id,
            claim_text=claim_text,
            subject=subject,
            predicate=predicate,
            object=object_text,
            source=source,
            extraction_method="spacy_dependency_parser",
            validation_status="PENDING",
            **qualifiers(claim_text)
        )

        claims.append(claim)

    return claims
