import json
import pymupdf as fitz
import pytest
from ingestion.pipeline import run_pipeline
from ingestion.pdf_loader import load_pdf
from ingestion.ocr import OcrUnavailable


def test_failed_extraction_does_not_replace_existing_corpus(tmp_path):
    raw = tmp_path / 'raw'
    raw.mkdir()
    (raw / 'empty.txt').write_text('')
    output = tmp_path / 'processed'
    output.mkdir()
    (output / 'chunks.jsonl').write_text('previous corpus')
    with pytest.raises(ValueError, match='existing corpus was preserved'):
        run_pipeline(raw, output)
    assert (output / 'chunks.jsonl').read_text() == 'previous corpus'
    assert len(json.loads((output / 'failures.json').read_text())) == 1


def test_pdf_keeps_readable_pages_when_ocr_is_missing(tmp_path, monkeypatch):
    path = tmp_path / 'mixed.pdf'
    with fitz.open() as doc:
        doc.new_page().insert_text((72, 72), 'Readable evidence.')
        doc.new_page()
        doc.save(path)

    def extract(page):
        text = page.get_text()
        if not text.strip():
            raise OcrUnavailable('Missing language data')
        return text, 'embedded'

    monkeypatch.setattr('ingestion.pdf_loader.extract_page', extract)
    doc = load_pdf(path)
    assert len(doc.sections) == 1 and doc.sections[0].location_number == 1
    assert doc.metadata['extraction_warnings'][0]['page'] == 2
    summary = run_pipeline(tmp_path, tmp_path / 'output')
    assert summary['documents_with_warnings'] == 1
    assert summary['succeeded'] == 1
