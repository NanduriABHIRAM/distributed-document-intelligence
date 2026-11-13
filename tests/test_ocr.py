import pymupdf as fitz
from fastapi.testclient import TestClient
from api.main import app
from ingestion.ocr import extract_page, extract_upload, OcrUnavailable


def test_embedded_pdf_text():
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Evidence from a digital PDF.")
        result = extract_upload(document.tobytes(), "pdf")
    assert "Evidence from a digital PDF." in result["text"]
    assert result["pages"][0]["method"] == "embedded"


def test_scanned_page_uses_ocr_and_force_overrides_embedded_text():
    class Page:
        def get_text(self, kind, textpage=None):
            return "Recognized scan" if textpage else "Embedded text"

        def get_textpage_ocr(self, **kwargs):
            assert kwargs == {"language": "eng", "dpi": 150, "full": True}
            return object()

    assert extract_page(Page()) == ("Embedded text", "embedded")
    assert extract_page(Page(), force=True) == ("Recognized scan", "ocr")


def test_ocr_endpoint_validation():
    client = TestClient(app)
    assert client.post("/documents/ocr?filename=test.exe", content=b"x").status_code == 415
    assert client.post("/documents/ocr?filename=test.pdf", content=b"").status_code == 400
    assert client.post("/documents/ocr?filename=test.pdf", content=b"invalid").status_code == 400
    assert client.post("/documents/ocr?filename=test.pdf&mode=wrong", content=b"x").status_code == 422


def test_missing_ocr_dependency_is_actionable(monkeypatch):
    def fail(*args):
        raise OcrUnavailable("OCR could not run. Install Tesseract English language data.")
    monkeypatch.setattr("api.routes.documents.extract_upload", fail)
    response = TestClient(app).post("/documents/ocr?filename=scan.png", content=b"image")
    assert response.status_code == 503
    assert "Tesseract" in response.json()["detail"]
