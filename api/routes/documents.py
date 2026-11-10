from fastapi import APIRouter

from api.data_store import documents

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/")
def list_documents():
    return {"items": documents(), "total": len(documents())}
