import hashlib

from evidence.schemas import EvidenceEvent, SourceReference


def generate_event_id(
    document_id: str,
    chunk_id: str,
    start: int,
    end: int
) -> str:

    raw_id = f"{document_id}:{chunk_id}:{start}:{end}"

    return hashlib.sha256(
        raw_id.encode("utf-8")
    ).hexdigest()[:16]


def get_phrase(token):
    """
    Get the complete phrase associated with a token.
    Example: 'the research team' instead of just 'team'.
    """

    tokens = list(token.subtree)

    start = min(t.i for t in tokens)
    end = max(t.i for t in tokens) + 1

    return token.doc[start:end].text.strip()


def extract_actor(sentence):
    """
    Identify who performed the action.
    Supports active and basic passive constructions.
    """

    # Active voice
    for token in sentence:
        if token.dep_ == "nsubj":
            return get_phrase(token)

    # Passive voice: look for an agent introduced by 'by'
    for token in sentence:
        if token.dep_ == "agent":
            for child in token.children:
                if child.dep_ == "pobj":
                    return get_phrase(child)

    return None


def extract_event_object(sentence):
    """
    Identify the object affected by the action.
    """

    object_dependencies = {
        "dobj",
        "obj",
        "dative",
        "attr",
        "oprd",
        "nsubjpass"
    }

    for token in sentence:

        if token.dep_ in object_dependencies:
            return get_phrase(token)

    return None


def extract_event_date(sentence):
    """
    Extract an explicit date or time from a sentence.
    """

    for entity in sentence.ents:

        if entity.label_ in {"DATE", "TIME"}:
            return entity.text

    return None


def extract_events(chunk: dict, nlp) -> list[EvidenceEvent]:

    text = chunk["text"]

    doc = nlp(text)

    events = []

    for sentence in doc.sents:

        # Identify the main action
        action_token = sentence.root

        # Skip sentences without a meaningful action
        if action_token.pos_ not in {"VERB", "AUX"}:
            continue

        action = action_token.lemma_

        actor = extract_actor(sentence)

        event_object = extract_event_object(sentence)

        # An event should have at least an identifiable actor
     