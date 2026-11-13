"""Text extraction shared by PDF ingestion and the OCR preview endpoint."""
import pymupdf as fitz


class OcrUnavailable(RuntimeError):
    pass


def extract_page(page, force=False):
    text = page.get_text("text")
    if text.strip() and not force:
        return text, "embedded"
    try:
        text_page = page.get_textpage_ocr(language="eng", dpi=150, full=True)
    except RuntimeError as error:
        raise OcrUnavailable(
            "OCR could not run. Install Tesseract English language data on the server "
            "and set TESSDATA_PREFIX to its tessdata directory."
        ) from error
    return page.get_text("text", textpage=text_page), "ocr"


def extract_upload(content: bytes, extension: str, force=False):
    with fitz.open(stream=content, filetype=extension) as source:
        if source.needs_pass:
            raise ValueError("Password-protected PDFs are not supported. Upload an unlocked copy.")
        if len(source) > 50:
            raise ValueError("Choose a document with 50 pages or fewer.")
        # Convert image documents to PDF pages for the shared OCR path.
        converted = None
        try:
            document = source
            if extension != "pdf":
                converted = fitz.open(stream=source.convert_to_pdf(), filetype="pdf")
                document = converted
            pages = []
            for number, page in enumerate(document, 1):
                if page.rect.width * page.rect.height > 20_000_000:
                    raise ValueError("Page dimensions are too large. Resize the scan and try again.")
                text, method = extract_page(page, force)
                pages.append({"page": number, "text": text, "method": method})
            return {"pages": pages, "text": "\n\n".join(page["text"] for page in pages)}
        finally:
            if converted is not None:
                converted.close()
