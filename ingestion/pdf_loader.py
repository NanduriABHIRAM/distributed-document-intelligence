from pathlib import Path
import pymupdf as fitz
from .base import ExtractedDocument, ExtractedSection
from .utils import sha256_file, document_id
from .ocr import extract_page, OcrUnavailable

def load_pdf(path: Path) -> ExtractedDocument:
    sections = []
    warnings = []
    with fitz.open(path) as doc:
        for number, page in enumerate(doc, start=1):
            try:
                text, _ = extract_page(page)
            except OcrUnavailable as error:
                warnings.append({"page": number, "error": str(error)})
                continue
            sections.append(ExtractedSection(text, "page", number))
        count = len(doc)
    if warnings and not any(section.text.strip() for section in sections):
        raise OcrUnavailable(f'No readable PDF pages. {warnings[0]["error"]}')
    return ExtractedDocument(document_id(path), str(path), "pdf", sections,
        {"filename": path.name, "page_count": count, "sha256": sha256_file(path),
         "extraction_warnings": warnings})
