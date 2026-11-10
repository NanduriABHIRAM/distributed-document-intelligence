from dataclasses import dataclass
from .cleaning import clean_text
from .utils import estimate_tokens, stable_id

@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    source_path: str
    file_type: str
    text: str
    start_offset: int
    end_offset: int
    location_type: str
    location_number: int | None
    chunk_index: int
    token_estimate: int
    metadata: dict

def chunk_section(section, document, chunk_size=1200, overlap=150, start_index=0):
    text = clean_text(section.text)
    if not text:
        return []
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > 0 and 0 <= overlap < chunk_size")
    chunks, start, index = [], 0, start_index
    while start < len(text):
        hard_end = min(start + chunk_size, len(text))
        end = hard_end
        if hard_end < len(text):
            candidates = [text.rfind(mark, start + chunk_size // 2, hard_end) for mark in ("\n", ". ", " ")]
            boundary = max(candidates)
            if boundary > start:
                end = boundary + (1 if text[boundary:boundary+1] == "\n" else 0)
        piece = text[start:end].strip()
        if piece:
            left_trim = len(text[start:end]) - len(text[start:end].lstrip())
            actual_start = start + left_trim
            actual_end = actual_start + len(piece)
            chunks.append(DocumentChunk(
                chunk_id=stable_id(document.document_id, str(index), str(actual_start), piece),
                document_id=document.document_id, source_path=document.source_path,
                file_type=document.file_type, text=piece, start_offset=actual_start,
                end_offset=actual_end, location_type=section.location_type,
                location_number=section.location_number, chunk_index=index,
                token_estimate=estimate_tokens(piece), metadata=document.metadata.copy()))
            index += 1
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks
