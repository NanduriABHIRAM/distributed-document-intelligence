from pathlib import Path
import fitz
from .base import ExtractedDocument, ExtractedSection
from .utils import sha256_file

def load_pdf(path: Path) -> ExtractedDocument:
    sections = []
    with fitz.open(path) as doc:
        for number, page in enumerate(doc, start=1):
            sections.append(ExtractedSection(page.get_text("text"), "page", number))
        count = len(doc)
    return ExtractedDocument(path.stem, str(path), "pdf", sections,
        {"filename": path.name, "page_count": count, "sha256": sha256_file(path)})
