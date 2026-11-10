from pathlib import Path
from .base import ExtractedDocument, ExtractedSection
from . import pdf_loader, docx_loader, pptx_loader, text_loader

SUPPORTED = {".pdf", ".docx", ".pptx", ".ppsx", ".txt", ".md"}

def load_document(path: Path) -> ExtractedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf": return pdf_loader.load_pdf(path)
    if suffix == ".docx": return docx_loader.load_docx(path)
    if suffix in {".pptx", ".ppsx"}: return pptx_loader.load_pptx(path)
    if suffix in {".txt", ".md"}: return text_loader.load_text(path)
    raise ValueError(f"Unsupported file type: {suffix}")

def discover_documents(input_dir: Path):
    return sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED and not p.name.startswith("~$"))
