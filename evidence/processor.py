"""Streaming coordinator for the reproducible Phase 2 evidence baseline."""

from __future__ import annotations

import argparse
import itertools
import json
import time
from dataclasses import asdict
from pathlib import Path

from evidence.claim_extractor import extract_claims
from evidence.entity_extractor import extract_entities, load_nlp
from evidence.event_extractor import extract_events
from evidence.evidence_builder import build_evidence
from evidence.evidence_validator import (
    validate_claims, validate_entities, validate_events, validate_relationships,
)
from evidence.relationship_extractor import extract_relationships


_OUTPUTS = ("entities", "claims", "events", "relationships")


def _write_jsonl(handle, records) -> None:
    for record in records:
        handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def process_evidence(
    chunks_path: str | Path, output_dir: str | Path, limit: int | None = None, batch_size: int = 32,
) -> dict:
    """Extract and validate evidence in bounded batches; the NLP parse runs once per chunk."""
    chunks_path, output_dir = Path(chunks_path), Path(output_dir)
    if not chunks_path.is_file():
        raise FileNotFoundError(f"Chunks file not found: {chunks_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    nlp = load_nlp()  # Load once per run: parser and NER are expensive resources.
    started = time.perf_counter()
    totals = {"chunks": 0, "entities": 0, "claims": 0, "events": 0, "relationships": 0, "invalid": 0}

    handles = {name: (output_dir / f"{name}.jsonl").open("w", encoding="utf-8") for name in _OUTPUTS}

    def parsed_chunks():
        with chunks_path.open("r", encoding="utf-8") as source:
            for line in source:
                if line.strip():
                    yield json.loads(line)

    def process_batch(chunks: list[dict]) -> None:
        # nlp.pipe avoids repeated model setup and is substantially faster than four parses per chunk.
        for chunk, doc in zip(chunks, nlp.pipe((item["text"] for item in chunks), batch_size=batch_size)):
            entities = validate_entities(chunk, extract_entities(chunk, nlp, doc))
            claims = validate_claims(chunk, extract_claims(chunk, nlp, doc))
            events = validate_events(chunk, extract_events(chunk, nlp, doc))
            relationships = validate_relationships(
                chunk, extract_relationships(chunk, entities, nlp, doc), entities,
            )
            bundle = build_evidence(chunk, entities, claims, events, relationships)
            for name in _OUTPUTS:
                records = getattr(bundle, name)
                _write_jsonl(handles[name], records)
                totals[name] += len(records)
                totals["invalid"] += sum(
                    1 for record in records
                    if getattr(record, "validation_status", "VALID") == "INVALID"
                )
            totals["chunks"] += 1

    try:
        chunks = itertools.islice(parsed_chunks(), limit) if limit is not None else parsed_chunks()
        while batch := list(itertools.islice(chunks, batch_size)):
            process_batch(batch)
    finally:
        for handle in handles.values():
            handle.close()

    elapsed = time.perf_counter() - started
    summary = {
        **totals,
        "elapsed_seconds": round(elapsed, 3),
        "chunks_per_second": round(totals["chunks"] / elapsed, 3) if elapsed else 0,
        "extractors": {"entities": "spacy_ner", "claims": "spacy_dependency_parser", "events": "rule_based_event_extractor", "relationships": "spacy_dependency_relationship_extractor"},
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract provenance-preserving evidence from chunks.")
    parser.add_argument("--chunks", default="data/processed/chunks.jsonl")
    parser.add_argument("--output", default="data/evidence")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    print(json.dumps(process_evidence(args.chunks, args.output, args.limit, args.batch_size), indent=2))


if __name__ == "__main__":
    main()
