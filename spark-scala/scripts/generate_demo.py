"""Create deterministic, synthetic inputs in the same schema as Python ingestion.

Run from any directory: python spark-scala/scripts/generate_demo.py
No models, network access, or personal documents are required.
"""
import json
from pathlib import Path


def generate(destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    evidence = destination / "evidence"
    evidence.mkdir(exist_ok=True)
    texts = [
        "Acme acquired Beta in 2023. The acquisition expanded its research team.",
        "Acme reported revenue of 100 million in 2024.",
        "Acme reported revenue of 120 million in 2024.",
        "Beta opened a research laboratory in Chennai in 2025.",
        "The research laboratory develops document retrieval and optical character recognition.",
        "The research laboratory develops document retrieval and optical character recognition.",
    ]
    chunks = [dict(chunk_id=f"c{i}", document_id=f"d{i // 2}", source_path=f"demo/report-{i // 2}.txt",
                   file_type="txt", text=text, start_offset=0, end_offset=len(text),
                   location_type="page", location_number=i % 2 + 1, chunk_index=i % 2,
                   token_estimate=len(text.split()), metadata={"synthetic": "true"})
              for i, text in enumerate(texts)]

    def source(i):
        chunk = chunks[i]
        return {key: chunk[key] for key in ("chunk_id", "document_id", "source_path", "location_type", "location_number", "start_offset", "end_offset")} | {"source_text": chunk["text"]}

    entities = [dict(entity_id=f"e{index}", text=text, normalized_text=text.lower(), entity_type=kind,
                     source=source(chunk), validation_status="VALID", extraction_method="synthetic_fixture")
                for index, (text, kind, chunk) in enumerate([
                    ("Acme", "ORGANIZATION", 0), ("Beta", "ORGANIZATION", 0),
                    ("Beta", "ORGANIZATION", 3), ("Chennai", "LOCATION", 3)])]
    relationships = [dict(relationship_id=f"r{i}", source_entity_id=a, target_entity_id=b,
                          relationship_type=kind, source=source(chunk), is_explicit=True, validation_status="VALID")
                     for i, (a, b, kind, chunk) in enumerate([
                         ("e0", "e1", "ACQUIRED", 0), ("e2", "e3", "OPENED_IN", 3)])]
    claims = [dict(claim_id=f"claim{i}", claim_text=texts[i], subject="Acme", predicate="reported revenue",
                   object=amount, event_date="2024", date_kind="explicit", negated=False, scope="annual revenue",
                   source=source(i), validation_status="VALID", extraction_method="synthetic_fixture")
              for i, amount in [(1, "100 million"), (2, "120 million")]]
    events = [dict(event_id="event0", event_type="ACQUISITION", action="acquired", actor="Acme", object="Beta",
                   event_date="2023", date_is_explicit=True, date_kind="explicit", negated=False,
                   source=source(0), validation_status="VALID", extraction_method="synthetic_fixture")]
    for path, records in [(destination / "chunks.jsonl", chunks), *[(evidence / f"{name}.jsonl", rows) for name, rows in
                          [("entities", entities), ("relationships", relationships), ("claims", claims), ("events", events)]]]:
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    print(f"Created {len(chunks)} chunks in {destination}")


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[1] / "demo")
