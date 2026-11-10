import json
from pathlib import Path
from dataclasses import asdict

def write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

def write_parquet(path: Path, records):
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("Parquet output requires pandas and pyarrow") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([asdict(r) for r in records]).to_parquet(path, index=False)
