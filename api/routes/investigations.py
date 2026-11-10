from fastapi import APIRouter
from pydantic import BaseModel, Field
from time import perf_counter

from api.data_store import search_chunks, get_graph
from evidence.catalog import analyze
from api.telemetry import retrieval_telemetry
from rag.answer_generator import generate_answer
from rag.context_builder import build_evidence_context, curate_evidence

router = APIRouter(prefix="/investigations", tags=["investigations"])

class InvestigationRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=6, ge=1, le=20)

@router.post("/query")
def investigate(payload: InvestigationRequest):
    started = perf_counter()
    results, retrieval = search_chunks(payload.query, payload.top_k)
    retrieval["latency_ms"] = round((perf_counter() - started) * 1_000, 2)
    retrieval_telemetry.record(retrieval["latency_ms"])
    if not results:
        return {
            "query": payload.query, "answer": generate_answer(payload.query, "", 0),
            "evidence": [], "conflicts": [], "retrieval": retrieval, "status": "insufficient_evidence",
        }
    curated = curate_evidence(results)
    graph = get_graph()
    for item in curated:
        item['claims'] = [claim for claim in graph.claims.values() if claim['source']['chunk_id'] == item['chunk_id']][:3]
        item['events'] = [event for event in graph.events.values() if event['source']['chunk_id'] == item['chunk_id']][:3]
    evidence = []
    for result in curated:
        evidence.append({
            "evidence_id": result["evidence_id"], "chunk_id": result["chunk_id"],
            "document_id": result["document_id"], "source_path": result["source_path"],
            "file_type": result["file_type"], "text": result["text"],
            "location_type": result.get("location_type"), "location_number": result.get("location_number"),
            "claims": result.get("claims", []),
            "events": result.get("events", []),
            "score": round(result.get("rrf_score", result.get("bm25_score", result.get("vector_score", 0.0))), 3),
        })
    analysis = analyze(graph, {item["chunk_id"] for item in curated})
    context = build_evidence_context(curated)
    return {
        "query": payload.query,
        "answer": generate_answer(payload.query, context, len(evidence), evidence=curated),
        "evidence": evidence,
        "conflicts": [item for item in analysis["comparisons"] if item["label"] == "contradiction"],
        "analysis": analysis,
        "retrieval": retrieval,
        "status": "ok",
    }
