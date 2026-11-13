"""Verify persisted Scala demo outputs: python verify_demo.py <output-prefix>."""
import json
import sys
from pathlib import Path
import pyarrow.parquet as pq


def verify(prefix: Path):
    def rows(suffix):
        return pq.read_table(str(prefix) + suffix).to_pylist()

    metrics_files = list(Path(str(prefix) + "-metrics").glob("part-*.json"))
    assert len(metrics_files) == 1, "Missing completion metrics"
    metrics = json.loads(metrics_files[0].read_text())
    assert metrics["chunks"] == 6
    assert metrics["entities"] == 4 and metrics["relationships"] == 2
    assert metrics["rejected_chunks"] == metrics["rejected_evidence"] == 0
    assert len(rows("")) == 6 and len(rows("-documents")) == 3
    assert rows("-quality") == []
    assert len(rows("-duplicate-content")) == 1
    assert rows("-duplicate-content")[0]["occurrences"] == 2
    nodes = {row["id"] for row in rows("-graph-nodes")}
    assert all(edge["source"] in nodes and edge["target"] in nodes for edge in rows("-graph-edges"))
    assert abs(sum(row["pagerank"] for row in rows("-graph-pagerank")) - 1.0) < 1e-9
    assert sum(row["chunks"] for row in rows("-partitions")) == 6
    assert len(rows("-timeline")) == 1
    assert rows("-claim-review")[0]["review_status"] == "CANDIDATE_REQUIRES_REVIEW"
    assert rows("-index-statistics")[0]["document_count"] == 6
    assert any(row["term"] == "laboratory" for row in rows("-terms"))
    print(json.dumps({"verification": "passed", "metrics": metrics}, indent=2))


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
