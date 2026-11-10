def make_source_reference(document_id: str, page: int | None, chunk_id: str, start: int | None = None, end: int | None = None) -> dict:
    return {
        "document_id": document_id,
        "page": page,
        "chunk_id": chunk_id,
        "char_start": start,
        "char_end": end,
    }
