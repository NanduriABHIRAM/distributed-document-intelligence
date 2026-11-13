from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.data_store import dashboard_stats
from api.telemetry import retrieval_telemetry
from api.routes.documents import router as documents_router
from api.routes.investigations import router as investigations_router
from api.routes.graph import router as graph_router
from api.routes.spark import router as spark_router

app = FastAPI(
    title="TraceRAG",
    description="Evidence-centric hybrid retrieval and grounded-answer API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(documents_router)
app.include_router(investigations_router)
app.include_router(graph_router)
app.include_router(spark_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "tracerag",
        "version": "0.2.0",
    }

@app.get("/dashboard")
def dashboard():
    return {**dashboard_stats(), "telemetry": retrieval_telemetry.snapshot()}
