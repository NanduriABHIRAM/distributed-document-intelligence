"""Non-blocking local Spark job control and persisted metrics inspection."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from threading import Lock
from time import time

from fastapi import APIRouter, HTTPException

from api.data_store import CHUNKS_PATH, EVIDENCE_DIR, ROOT
from configs.runtime import option

router = APIRouter(prefix="/spark", tags=["spark"])
_lock = Lock()
_process: subprocess.Popen | None = None
_started_at: float | None = None


def _output_path() -> Path:
    value = Path(option("spark", "output_path", "data/spark-output", "SPARK_OUTPUT_PATH"))
    return value if value.is_absolute() else ROOT / value


def _metrics() -> dict | None:
    directory = Path(f"{_output_path()}-metrics")
    for path in sorted(directory.glob("*.json"), reverse=True):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return None


@router.get("/status")
def status():
    with _lock:
        running = _process is not None and _process.poll() is None
        exit_code = None if running or _process is None else _process.returncode
    return {"state": "running" if running else "completed" if exit_code == 0 else "failed" if exit_code is not None else "not_started",
            "started_at": _started_at, "exit_code": exit_code, "metrics": _metrics(),
            "output_path": str(_output_path())}


@router.post("/run", status_code=202)
def run():
    """Start a configured local Spark job without tying up an HTTP worker."""
    global _process, _started_at
    with _lock:
        if _process is not None and _process.poll() is None:
            raise HTTPException(status_code=409, detail="A Spark job is already running")
        executable = shutil.which("spark-submit")
        if not executable:
            raise HTTPException(status_code=503, detail="spark-submit is not installed on this server")
        jar = ROOT / option("spark", "jar_path", "spark-scala/target/scala-2.12/distributed-document-intelligence-etl_2.12-0.1.0.jar", "SPARK_JAR_PATH")
        if not jar.is_file():
            raise HTTPException(status_code=503, detail="Spark job JAR is not built; run sbt package first")
        output = _output_path()
        if output.exists():
            raise HTTPException(status_code=409, detail="Configured Spark output already exists; choose a new output path")
        master = option("spark", "master", "local[*]", "SPARK_MASTER")
        partitions = str(option("spark", "partitions", 4, "SPARK_PARTITIONS"))
        command = [executable, "--class", "DocumentETL", "--master", str(master), str(jar),
                   str(CHUNKS_PATH), str(output), partitions, str(EVIDENCE_DIR)]
        _process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _started_at = time()
    return {"state": "started", "output_path": str(output)}
