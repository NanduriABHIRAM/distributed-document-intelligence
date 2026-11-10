"""Read-only access to local processing artefacts for the web API."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from retrieval.bm25_retriever import BM25Retriever


ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"
EVIDENCE_DIR = ROOT / "data" / "evidence"


@lru_cache(maxsize=1)
def load_chunks() -> tuple[dict, ...]:
    if not CHUNKS_PATH.exists():
        return ()
    with CHUNKS_PATH.open("r", encoding="utf-8") as source:
        return tuple(json.loads(line) for line in source if line.strip())


@lru_cache(maxsize=1)
def get_retriever() -> BM25Retriever:
    retriever = BM25Retriever()
    retriever.fit(list(load_chunks()))
    return retriever


def documents() -> list[dict]:
    grouped: dict[str, dict] = {}
    for chunk in load_chunks():
        item = grouped.setdefault(chunk["document_id"], {
            "document_id": chunk["document_id"], "source_path": chunk["source_path"],
            "file_type": chunk["file_type"], "chunk_count": 0,
        })
        item["chunk_count"] += 1
    return sorted(grouped.values(), key=lambda item: item["document_id"].casefold())


def dashboard_stats() -> dict:
    summary_path = ROOT / "data" / "processed" / "summary.json"
    ingestion = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    evidence_summary = EVIDENCE_DIR / "summary.json"
    evidence = json.loads(evidence_summary.read_text(encoding="utf-8")) if evidence_summary.exists() else None
    document_records = documents()
    return {
        "documents": len(document_records),
        "source_files": ingestion.get("succeeded", len(document_records)),
        "chunks": ingestion.get("chunks", len(load_chunks())),
        "evidence": evidence,
        "retrieval": "BM25 lexical baseline",
    }
