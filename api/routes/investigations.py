from fastapi import APIRouter, HTTPException
from typing import Literal
from pydantic import BaseModel, Field
from time import perf_counter

from api.data_store import search_chunks, get_graph
from evidence.catalog import analyze
from api.telemetry import retrieval_telemetry
from rag.answer_generator import generate_answer
from rag.context_builder import build_evidence_context, curate_evidence
from rag.study_assistant import generate_study_answer, retrieval_question
from rag.ollama_client import OllamaClient, OllamaError, OllamaTimeoutError

router = APIRouter(prefix="/investigations", tags=["investigations"])

class InvestigationRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=6, ge=1, le=20)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class StudyRequest(InvestigationRequest):
    history: list[ChatMessage] = Field(default_factory=list, max_length=8)
    style: Literal["notes", "summary", "explain"] = "notes"
    allow_general: bool = True


@router.post("/chat")
def study_chat(payload: StudyRequest):
    client = OllamaClient(timeout=120)
    if not client.model_available():
        raise HTTPException(503, f"The study tutor needs Ollama with {client.model}. Run 'ollama pull {client.model}' and 'ollama serve', then retry.")
    history = [item.model_dump() for item in payload.history]
    started = perf_counter()
    results, retrieval = search_chunks(retrieval_question(payload.query, history), payload.top_k)
    retrieval["latency_ms"] = round((perf_counter() - started) * 1000, 2)
    evidence = curate_evidence(results)
    try:
        answer = generate_study_answer(payload.query, evidence, history, payload.style, payload.allow_general, client)
    except OllamaTimeoutError as error:
        raise HTTPException(504, "The tutor took too long. Try a shorter question or fewer source passages.") from error
    except OllamaError as error:
        raise HTTPException(502, str(error)) from error
    public_evidence = [{key: item.get(key) for key in (
        "evidence_id", "chunk_id", "document_id", "source_path", "file_type", "text", "location_type", "location_number"
    )} for item in evidence]
    return {"query": payload.query, "answer": answer, "evidence": public_evidence, "retrieval": retrieval}

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
