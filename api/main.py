from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.data_store import dashboard_stats
from api.routes.documents import router as documents_router
from api.routes.investigations import router as investigations_router

app = FastAPI(
    title="Distributed Document Intelligence",
    description="Evidence-centric document intelligence API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(documents_router)
app.include_router(investigations_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "distributed-document-intelligence",
        "version": "0.1.0",
    }

@app.get("/dashboard")
def dashboard():
    return dashboard_stats()
