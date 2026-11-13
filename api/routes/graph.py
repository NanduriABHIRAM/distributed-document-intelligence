"""Read-only API for the persisted local evidence graph.

The graph is rebuilt from validated JSONL evidence records, so it works without
Neo4j during local development and never invents visualisation data.
"""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, HTTPException, Query

from api.data_store import get_graph, rebuild_graph


router = APIRouter(prefix="/graph", tags=["graph"])


def _node(record: dict) -> dict:
    source = record.get("source", {})
    return {
        "id": record["entity_id"],
        "label": record.get("text") or record.get("normalized_text") or record["entity_id"],
        "entity_type": record.get("entity_type", "OTHER"),
        "document_id": source.get("document_id"),
        "chunk_id": source.get("chunk_id"),
        "source": source,
    }


def _relationship_edges(graph: object, visible_ids: set[str]) -> list[dict]:
    edges, seen = [], set()
    for edge in graph.edges:
        if edge["type"] != "RELATED_TO" or edge["source"] not in visible_ids or edge["target"] not in visible_ids:
            continue
        evidence = edge.get("evidence", {})
        relationship_id = evidence.get("evidence_id")
        if not relationship_id or relationship_id in seen:
            continue
        seen.add(relationship_id)
        edges.append({
            "id": relationship_id,
            "source": edge["source"],
            "target": edge["target"],
            "label": evidence.get("predicate", "RELATED_TO"),
            "relationship_type": evidence.get("predicate", "RELATED_TO"),
            "provenance": evidence,
        })
    return edges


def graph_payload(document_id: str | None = None, entity_type: str | None = None, search: str | None = None, limit: int = 800) -> dict:
    graph = get_graph()
    nodes = [_node(record) for record in graph.entities.values()]
    if document_id:
        nodes = [node for node in nodes if node["document_id"] == document_id]
    if entity_type:
        nodes = [node for node in nodes if node["entity_type"].casefold() == entity_type.casefold()]
    if search:
        needle = search.casefold().strip()
        nodes = [node for node in nodes if needle in node["label"].casefold()]
    nodes.sort(key=lambda node: (node["label"].casefold(), node["id"]))
    candidates = {node["id"] for node in nodes}
    # Prioritise real relationship endpoints, so a bounded graph remains useful
    # for a 175k-entity corpus instead of downloading an unusable SVG payload.
    relation_ids = {endpoint for edge in _relationship_edges(graph, candidates)
                    for endpoint in (edge["source"], edge["target"])}
    nodes.sort(key=lambda node: (node["id"] not in relation_ids, node["label"].casefold(), node["id"]))
    truncated = len(nodes) > limit
    nodes = nodes[:limit]
    node_ids = {node["id"] for node in nodes}
    return {"nodes": nodes, "edges": _relationship_edges(graph, node_ids), "truncated": truncated,
            "filters": {"document_id": document_id, "entity_type": entity_type, "search": search}}


@router.get("")
def graph(document_id: str | None = Query(default=None), entity_type: str | None = Query(default=None),
          search: str | None = Query(default=None, max_length=200), limit: int = Query(default=800, ge=1, le=5000)):
    return graph_payload(document_id, entity_type, search, limit)


@router.get("/stats")
def graph_stats():
    graph = get_graph()
    all_edges = _relationship_edges(graph, set(graph.entities))
    return {
        "nodes": len(graph.entities),
        "edges": len(all_edges),
        "entity_types": dict(sorted(Counter(item.get("entity_type", "OTHER") for item in graph.entities.values()).items())),
        "relationship_types": dict(sorted(Counter(edge["relationship_type"] for edge in all_edges).items())),
        "documents": len(graph.documents),
        "source": "local_validated_evidence",
    }


@router.get("/entities/{entity_id}")
def entity(entity_id: str):
    graph = get_graph()
    record = graph.entities.get(entity_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    node = _node(record)
    aliases = [other for other in graph.entities.values()
               if other.get("entity_type") == record.get("entity_type")
               and other.get("normalized_text") == record.get("normalized_text")]
    node["supporting_evidence"] = [_node(other)["source"] for other in aliases]
    node["source_documents"] = sorted({item["source"].get("document_id") for item in aliases if item.get("source")})
    node["relationships"] = [edge for edge in _relationship_edges(graph, set(graph.entities))
                             if edge["source"] == entity_id or edge["target"] == entity_id]
    return node


@router.get("/relationships/{relationship_id}")
def relationship(relationship_id: str):
    graph = get_graph()
    for edge in _relationship_edges(graph, set(graph.entities)):
        if edge["id"] == relationship_id:
            return edge
    raise HTTPException(status_code=404, detail="Relationship not found")


@router.post("/rebuild")
def rebuild():
    graph = rebuild_graph()
    payload = graph_payload(limit=800)
    return {"status": "rebuilt", "nodes": len(payload["nodes"]), "edges": len(payload["edges"]),
            "documents": len(graph.documents), "chunks": len(graph.chunks)}
