"""Read-only access to local processing artefacts for the web API."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from retrieval.bm25_retriever import BM25Retriever
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.ollama_client import OllamaEmbedder
from retrieval.vector_retriever import VectorRetriever
from rag.ollama_client import OllamaClient


ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"
EVIDENCE_DIR = ROOT / "data" / "evidence"
VECTOR_INDEX_PATH = ROOT / "data" / "processed" / "chunks.faiss"
VECTOR_RECORDS_PATH = ROOT / "data" / "processed" / "chunks.vectors.json"
VECTOR_METADATA_PATH = ROOT / "data" / "processed" / "chunks.vectors.meta.json"


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


@lru_cache(maxsize=4)
def _load_vector_retriever(index_mtime_ns: int, records_mtime_ns: int) -> VectorRetriever:
    return VectorRetriever.load(VECTOR_INDEX_PATH, VECTOR_RECORDS_PATH, OllamaEmbedder())


def get_vector_retriever() -> VectorRetriever | None:
    """Load a ready index only; indexing is an explicit CLI operation."""
    if not VECTOR_INDEX_PATH.exists() or not VECTOR_RECORDS_PATH.exists() or not VECTOR_METADATA_PATH.exists():
        return None
    metadata = json.loads(VECTOR_METADATA_PATH.read_text(encoding="utf-8"))
    if not metadata.get("complete", False):
        return None
    return _load_vector_retriever(VECTOR_INDEX_PATH.stat().st_mtime_ns, VECTOR_RECORDS_PATH.stat().st_mtime_ns)


def search_chunks(query: str, top_k: int) -> tuple[list[dict], dict]:
    """Prefer hybrid search, but keep the service usable when local embeddings fail."""
    dense = get_vector_retriever()
    try:
        return HybridRetriever(get_retriever(), dense).search(query, top_k)
    except Exception as error:
        results = get_retriever().search(query, top_k)
        return results, {"mode": "bm25_fallback", "reason": type(error).__name__, "lexical_candidates": len(results), "dense_candidates": 0}


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
    vector_metadata = json.loads(VECTOR_METADATA_PATH.read_text(encoding="utf-8")) if VECTOR_METADATA_PATH.exists() else None
    generation_client = OllamaClient()
    return {
        "documents": len(document_records),
        "source_files": ingestion.get("succeeded", len(document_records)),
        "chunks": ingestion.get("chunks", len(load_chunks())),
        "evidence": evidence,
        "retrieval": "hybrid RRF" if get_vector_retriever() else "BM25 (dense index not built)",
        "dense_index_ready": get_vector_retriever() is not None,
        "embeddings_generated": vector_metadata.get("vector_count", 0) if vector_metadata else 0,
        "embedding_model": vector_metadata.get("embedding_model") if vector_metadata else None,
        "generation_model": generation_client.model,
        "generation_model_available": generation_client.model_available(),
    }
