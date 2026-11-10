from rag.context_builder import build_evidence_context, curate_evidence


def test_curated_evidence_and_prompt_share_exact_citation_ids():
    results = [
        {"chunk_id": "a", "document_id": "doc-a", "text": "A source statement.", "location_type": "page", "location_number": 1},
        {"chunk_id": "duplicate", "document_id": "doc-a", "text": "A source statement.", "location_type": "page", "location_number": 2},
        {"chunk_id": "b", "document_id": "doc-b", "text": "Another source statement.", "location_type": "page", "location_number": 3},
    ]
    curated = curate_evidence(results)
    context = build_evidence_context(curated)
    assert [item["evidence_id"] for item in curated] == ["E1", "E2"]
    assert "[E1]" in context and "[E2]" in context
    assert "duplicate" not in context
