
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from pptx import Presentation
from .base import ExtractedDocument, ExtractedSection
from .utils import sha256_file


def load_pptx(path: Path) -> ExtractedDocument:

    # Handle PPSX slideshow files
    if path.suffix.lower() == ".ppsx":
        source = BytesIO()

        with ZipFile(path, "r") as original:
            with ZipFile(source, "w", ZIP_DEFLATED) as converted:

                for item in original.infolist():
                    data = original.read(item.filename)

                    if item.filename == "[Content_Types].xml":
                        data = data.replace(
                            b"application/vnd.openxmlformats-officedocument.presentationml.slideshow.main+xml",
                            b"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
                        )

                    converted.writestr(item, data)

        source.seek(0)
        presentation = Presentation(source)

    else:
        presentation = Presentation(str(path))

    sections = []

    for number, slide in enumerate(presentation.slides, start=1):
        parts = []

        for shape in slide.shapes:

            if shape.has_text_frame:
                if shape.text.strip():
                    parts.append(shape.text)

            if shape.has_table:
                for row in shape.table.rows:
                    parts.append(
                        " | ".join(cell.text.strip() for cell in row.cells)
                    )

        sections.append(
            ExtractedSection(
                "\n".join(parts),
                "slide",
                number
            )
        )

    return ExtractedDocument(
        document_id=path.stem,
        source_path=str(path),
        file_type=path.suffix.lower().lstrip("."),
        sections=sections,
        metadata={
            "filename": path.name,
            "slide_count": len(sections),
            "sha256": sha256_file(path)
        }
    )
