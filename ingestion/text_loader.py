from pathlib import Path
from .base import ExtractedDocument, ExtractedSection
from .utils import sha256_file, document_id

def load_text(path: Path) -> ExtractedDocument:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return ExtractedDocument(document_id(path), str(path), path.suffix.lower().lstrip("."),
        [ExtractedSection(text, "document", None)],
        {"filename": path.name, "sha256": sha256_file(path)})
