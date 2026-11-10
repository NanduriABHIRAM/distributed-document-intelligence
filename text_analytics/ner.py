"""Standalone NER utility for experiments outside the evidence processor."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _nlp():
    import spacy
    return spacy.load("en_core_web_sm")


def extract_entities(text: str) -> list[dict]:
    return [
        {"text": entity.text, "label": entity.label_, "start_offset": entity.start_char, "end_offset": entity.end_char}
        for entity in _nlp()(text).ents
    ]
