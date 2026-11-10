from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.data_store import get_retriever
from rag.answer_generator import generate_answer
from rag.context_builder import build_evidence_context

router = APIRouter(prefix="/investigations", tags=["investigations"])

class InvestigationRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=6, ge=1, le=20)

@router.post("/query")
def investigate(payload: InvestigationRequest):
    results = get_retriever().search(payload.query, top_k=payload.top_k)
    if not results:
        return {
            "query": payload.query, "answer": generate_answer(payload.query, "", 0),
            "evidence": [], "conflicts": [], "status": "insufficient_evidence",
        }
    evidence = []
    for position, result in enumerate(results, start=1):
        evidence.append({
            "evidence_id": f"E{position}", "chunk_id": result["chunk_id"],
            "document_id": result["document_id"], "source_path": result["source_path"],
            "file_type": result["file_type"], "text": result["text"],
            "location_type": result.get("location_type"), "location_number": result.get("location_number"),
            "score": round(result["bm25_score"], 3),
        })
    context = build_evidence_context(results)
    return {
        "query": payload.query,
        "answer": generate_answer(payload.query, context, len(evidence)),
        "evidence": evidence,
        "conflicts": [],
        "status": "ok",
    }
