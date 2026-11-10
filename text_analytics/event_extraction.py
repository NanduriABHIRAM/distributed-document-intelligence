"""Experimental event extraction with original sentence offsets."""

from __future__ import annotations

from text_analytics.ner import _nlp


def extract_events(text: str) -> list[dict]:
    events = []
    for sentence in _nlp()(text).sents:
        for verb in sentence:
            if verb.pos_ != "VERB":
                continue
            actor = next((child.text for child in verb.children if child.dep_ in {"nsubj", "nsubjpass"}), None)
            if actor is None:
                continue
            event_date = next((entity.text for entity in sentence.ents if entity.label_ in {"DATE", "TIME"}), None)
            events.append({"action": verb.lemma_, "actor": actor, "text": sentence.text, "event_date": event_date, "start_offset": sentence.start_char, "end_offset": sentence.end_char})
    return events
