from fastapi.testclient import TestClient


def test_graph_api_returns_only_real_relationships(monkeypatch):
    from api.main import app
    import api.routes.graph as route
    from evidence.evidence_graph import EvidenceGraph

    graph = EvidenceGraph()
    chunk = {"chunk_id": "c1", "document_id": "d1", "source_path": "source.txt", "text": "Acme acquired Beta."}
    graph.add_chunk(chunk)
    graph.add_entity({"entity_id": "e1", "text": "Acme", "normalized_text": "acme", "entity_type": "ORGANIZATION", "source": {**chunk, "source_text": chunk["text"], "start_offset": 0, "end_offset": 4}})
    graph.add_entity({"entity_id": "e2", "text": "Beta", "normalized_text": "beta", "entity_type": "ORGANIZATION", "source": {**chunk, "source_text": chunk["text"], "start_offset": 14, "end_offset": 18}})
    graph.link_evidence([{ "relationship_id": "r1", "source_entity_id": "e1", "target_entity_id": "e2", "relationship_type": "ACQUIRED", "validation_status": "VALID", "source": {**chunk, "source_text": chunk["text"]}}])
    monkeypatch.setattr(route, "get_graph", lambda: graph)
    response = TestClient(app).get("/graph")
    assert response.status_code == 200
    assert [node["id"] for node in response.json()["nodes"]] == ["e1", "e2"]
    assert response.json()["edges"][0]["id"] == "r1"
    assert TestClient(app).get("/graph/entities/e1").json()["source_documents"] == ["d1"]


def test_empty_graph_is_honest(monkeypatch):
    from api.main import app
    import api.routes.graph as route
    from evidence.evidence_graph import EvidenceGraph
    monkeypatch.setattr(route, "get_graph", EvidenceGraph)
    response = TestClient(app).get("/graph/stats")
    assert response.status_code == 200
    assert response.json()["nodes"] == response.json()["edges"] == 0
