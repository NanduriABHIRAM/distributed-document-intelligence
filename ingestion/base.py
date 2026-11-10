from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

@dataclass
class ExtractedSection:
    text: str
    location_type: str = "document"  # document, page, or slide
    location_number: int | None = None

@dataclass
class ExtractedDocument:
    document_id: str
    source_path: str
    file_type: str
    sections: list[ExtractedSection]
    metadata: dict = field(default_factory=dict)

class DocumentLoader(Protocol):
    def load(self, path: Path) -> ExtractedDocument: ...
