import argparse
from pathlib import Path
from .pipeline import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="Phase 1 document ingestion pipeline")
    parser.add_argument("--input", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument("--parquet", action="store_true", help="Also write chunks.parquet (requires pyarrow)")
    args = parser.parse_args()
    run_pipeline(args.input, args.output, args.chunk_size, args.overlap, args.parquet)

if __name__ == "__main__":
    main()
