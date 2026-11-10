"""CLI that builds a persistent BGE-M3/Ollama FAISS index from processed chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from retrieval.ollama_client import OllamaEmbedder
from retrieval.vector_retriever import VectorRetriever


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(
    chunks_path: str, index_path: str, records_path: str, batch_size: int = 8,
    checkpoint_every: int = 10, limit: int | None = None, resume: bool = False,
) -> dict:
    if batch_size < 1 or checkpoint_every < 1 or (limit is not None and limit < 1):
        raise ValueError("Batch size, checkpoint interval and limit must be positive")
    chunks_file = Path(chunks_path)
    total_chunks = sum(1 for line in chunks_file.open("r", encoding="utf-8") if line.strip())
    retriever = (
        VectorRetriever.load(index_path, records_path, OllamaEmbedder())
        if resume and Path(index_path).exists() and Path(records_path).exists()
        else VectorRetriever(embedder=OllamaEmbedder())
    )
    indexed = len(retriever.records)
    target = min(total_chunks, limit) if limit is not None else total_chunks
    digest = _file_hash(chunks_file)
    if resume and indexed:
        meta = json.loads(Path(records_path).with_suffix('.meta.json').read_text(encoding='utf-8'))
        if meta.get('chunks_sha256') != digest:
            raise ValueError('Corpus changed; cannot resume this index')


    def checkpoint(complete: bool) -> None:
        if retriever.index is not None:
            retriever.save(index_path, records_path, {
                "embedding_model": retriever.embedder.model,
                "chunks_sha256": digest,
                "batch_size": batch_size,
                "total_chunks": total_chunks,
                "complete": complete,
            })

    with Path(chunks_path).open("r", encoding="utf-8") as source:
        batch = []
        for position, line in enumerate(line for line in source if line.strip()):
            if position < indexed:
                continue
            if indexed + len(batch) >= target:
                break
            batch.append(json.loads(line))
            if len(batch) == batch_size:
                retriever.add(batch)
                indexed += len(batch)
                batch = []
                if indexed % (batch_size * checkpoint_every) == 0:
                    checkpoint(False)
                    print(f"Indexed {indexed}/{target} chunks", flush=True)
        if batch:
            retriever.add(batch)
            indexed += len(batch)
    complete = indexed == total_chunks and limit is None
    checkpoint(complete)
    return {"chunks_indexed": indexed, "total_chunks": total_chunks, "complete": complete, "index_path": index_path, "records_path": records_path, "embedding_model": retriever.embedder.model}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build TraceRAG's persistent dense vector index.")
    parser.add_argument("--chunks", default="data/processed/chunks.jsonl")
    parser.add_argument("--index", default="data/processed/chunks.faiss")
    parser.add_argument("--records", default="data/processed/chunks.vectors.json")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.chunks, args.index, args.records, args.batch_size, args.checkpoint_every, args.limit, args.resume), indent=2))
