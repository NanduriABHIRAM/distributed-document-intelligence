from pathlib import Path
from docx import Document
from .base import ExtractedDocument, ExtractedSection
from .utils import sha256_file

def load_docx(path: Path) -> ExtractedDocument:
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return ExtractedDocument(path.stem, str(path), "docx",
        [ExtractedSection("\n".join(parts), "document", None)],
        {"filename": path.name, "sha256": sha256_file(path)})
