"""Package source, built frontend, demo, and Scala JAR without local secrets/data."""
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = (
    "api", "configs", "embeddings", "evaluation", "evidence", "ingestion", "rag",
    "retrieval", "text_analytics", "tests", "scripts", "docs", "frontend/src",
    "frontend/dist", "spark-scala/src", "spark-scala/demo", "spark-scala/scripts",
)
ROOT_FILES = (
    "README.md", "requirements.txt", "requirements-lock.txt", ".gitignore", ".env.example", "compose.yaml",
    "frontend/package.json", "frontend/package-lock.json", "frontend/index.html",
    "frontend/tsconfig.json", "frontend/tsconfig.node.json", "frontend/vite.config.ts",
    "spark-scala/build.sbt", "spark-scala/README.md", "spark-scala/project/build.properties",
    "spark-scala/project/repositories",
    "spark-scala/target/scala-2.12/distributed-document-intelligence-etl_2.12-0.1.0.jar",
)


def package():
    files = {ROOT / name for name in ROOT_FILES if (ROOT / name).is_file()}
    for directory in SOURCE_DIRS:
        files.update(path for path in (ROOT / directory).rglob("*") if path.is_file()
                     and not any(part in {"__pycache__", "node_modules", ".pytest_cache"} for part in path.parts)
                     and path.suffix not in {".pyc", ".log"}
                     and not path.name.startswith(".env"))
    output = ROOT / "releases" / "TraceRAG-final-project.zip"
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, "TraceRAG/" + path.relative_to(ROOT).as_posix())
    with ZipFile(output) as archive:
        assert archive.testzip() is None, "Archive integrity check failed"
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(f"Packaged {len(files)} files: {output} ({output.stat().st_size:,} bytes)")
    print(f"SHA256: {digest}")


if __name__ == "__main__":
    package()
