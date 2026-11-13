import argparse
import json
from pathlib import Path
from .pipeline import run_pipeline
from .loaders import discover_documents, SUPPORTED
from configs.runtime import option

def main():
    parser = argparse.ArgumentParser(description="Discover documents, extract text, and build the UI retrieval corpus")
    parser.add_argument("--input", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    parser.add_argument("--chunk-size", type=int, default=int(option("processing", "chunk_size", 1200)))
    parser.add_argument("--overlap", type=int, default=int(option("processing", "chunk_overlap", 150)))
    parser.add_argument("--parquet", action="store_true", help="Also write chunks.parquet (requires pyarrow)")
    parser.add_argument("--scan-only", action="store_true", help="List supported files without changing the corpus")
    args = parser.parse_args()
    input_dir, output_dir = args.input.expanduser().resolve(), args.output.expanduser().resolve()
    print(f"Input:  {input_dir}", flush=True)
    print(f"Output: {output_dir}", flush=True)
    if not input_dir.is_dir():
        parser.exit(1, f"Input folder does not exist: {input_dir}\nUse --input with the folder containing your documents.\n")
    paths = discover_documents(input_dir)
    print(f"Found {len(paths)} supported documents (including subfolders).", flush=True)
    if not paths:
        parser.exit(1, f"Supported formats: {', '.join(sorted(SUPPORTED))}. Legacy .doc files must be saved as .docx.\n")
    if args.scan_only:
        for path in paths:
            print(path.relative_to(input_dir))
        return
    try:
        summary = run_pipeline(input_dir, output_dir, args.chunk_size, args.overlap, args.parquet,
                               progress=lambda message: print(message, flush=True))
    except (ValueError, OSError) as error:
        parser.exit(1, f"Ingestion failed: {error}\n")
    print(json.dumps(summary, indent=2), flush=True)
    if summary["failed"]:
        print(f"Some documents failed. Details: {output_dir / 'failures.json'}", flush=True)
    print("Corpus written. Refresh the document library in the UI.", flush=True)

if __name__ == "__main__":
    main()
