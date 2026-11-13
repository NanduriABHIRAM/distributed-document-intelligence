from types import SimpleNamespace

from fastapi.testclient import TestClient
from api.main import app
import api.routes.spark as route


def setup_runtime(tmp_path, monkeypatch):
    jar = tmp_path / "job.jar"
    jar.write_bytes(b"fixture")
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text("{}\n")
    monkeypatch.setattr(route, "_process", None)
    monkeypatch.setattr(route, "ROOT", tmp_path)
    monkeypatch.setattr(route, "CHUNKS_PATH", chunks)
    monkeypatch.setattr(route, "EVIDENCE_DIR", tmp_path / "missing-evidence")
    monkeypatch.setattr(route, "_output_path", lambda: tmp_path / "new-parent" / "output")
    monkeypatch.setattr(route, "option", lambda section, key, default, env: str(jar) if key == "jar_path" else default)
    monkeypatch.setattr(route.shutil, "which", lambda name: "spark-submit")


def test_missing_runtime_is_reported(monkeypatch):
    monkeypatch.setattr(route, "_process", None)
    monkeypatch.setattr(route.shutil, "which", lambda name: None)
    assert TestClient(app).post("/spark/run").status_code == 503


def test_launch_without_optional_evidence_and_keep_log(tmp_path, monkeypatch):
    setup_runtime(tmp_path, monkeypatch)
    commands = []

    def launch(command, **kwargs):
        commands.append(command)
        kwargs["stdout"].write(b"Spark log fixture\n")
        return SimpleNamespace(poll=lambda: None)

    monkeypatch.setattr(route.subprocess, "Popen", launch)
    client = TestClient(app)
    assert client.post("/spark/run").status_code == 202
    assert str(route.EVIDENCE_DIR) not in commands[0]
    assert (tmp_path / "logs/spark-job.log").read_text() == "Spark log fixture\n"
    assert client.get("/spark/status").json()["state"] == "running"
    assert client.post("/spark/run").status_code == 409


def test_partial_output_blocks_accidental_retry(tmp_path, monkeypatch):
    setup_runtime(tmp_path, monkeypatch)
    output = route._output_path()
    output.parent.mkdir()
    output.with_name(output.name + "-quality").mkdir()
    assert TestClient(app).post("/spark/run").status_code == 409
