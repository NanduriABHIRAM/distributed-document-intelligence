from pathlib import Path
from .loaders import discover_documents, load_document
from .chunking import chunk_section
from .storage import write_jsonl, write_parquet

def run_pipeline(input_dir: Path, output_dir: Path, chunk_size=1200, overlap=150, parquet=False):
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    paths = discover_documents(input_dir)
    all_chunks, failures, successes = [], [], 0
    for path in paths:
        try:
            document = load_document(path)
            index = 0
            for section in document.sections:
                chunks = chunk_section(section, document, chunk_size, overlap, index)
                all_chunks.extend(chunks)
                index += len(chunks)
            successes += 1
            print(f"[OK] {path.name}")
        except Exception as exc:
            failures.append({"source_path": str(path), "error": f"{type(exc).__name__}: {exc}"})
            print(f"[FAILED] {path.name}: {type(exc).__name__}: {exc}")
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "chunks.jsonl", all_chunks)
    if parquet:
        write_parquet(output_dir / "chunks.parquet", all_chunks)
    (output_dir / "failures.json").write_text(__import__("json").dumps(failures, indent=2), encoding="utf-8")
    summary = {"discovered": len(paths), "succeeded": successes, "failed": len(failures), "chunks": len(all_chunks)}
    (output_dir / "summary.json").write_text(__import__("json").dumps(summary, indent=2), encoding="utf-8")
    print("\nIngestion summary")
    for key, value in summary.items(): print(f"{key}: {value}")
    return summary
