# TraceRAG â€” Evidence-Centric Hybrid Retrieval-Augmented Generation

A research-oriented evidence intelligence platform for large document collections.
It combines distributed document processing, claim extraction, evidence graphs,
contradiction detection, temporal reasoning, hybrid retrieval, and evidence-grounded QA.

## Research focus

**Evidence-Centric Hybrid Retrieval (ECHR):** combine lexical and semantic retrieval
with graph-based evidence relationships and temporal relevance.

The current baseline includes complete local ingestion, provenance-preserving
evidence extraction, lexical and dense retrieval adapters, graph expansion,
temporal and contradiction baselines, evaluation metrics, a FastAPI
investigation API, and a React evidence workspace. SentenceTransformer models,
FAISS indexes, Neo4j, and local LLM generation are optional runtime integrations
that must be configured and evaluated before research results are reported.

## Architecture

1. Ingestion: PDF, DOCX, PPTX, TXT, Markdown
2. Distributed ETL: Apache Spark + Scala
3. Text analytics: cleaning, NER, claim and event extraction
4. Evidence: claim matching, contradiction detection, temporal reasoning, provenance
5. Storage: PostgreSQL metadata, Neo4j graph, FAISS vectors, BM25 lexical index
6. Retrieval: BM25 + vector + RRF + graph expansion + temporal/evidence reranking
7. RAG: answer generation with source citation validation
8. Evaluation: retrieval, contradiction, temporal, answer quality, scalability

## Repository layout

- `ingestion/` document loading and parsing
- `spark-scala/` distributed ETL project
- `text_analytics/` NLP and structured extraction
- `evidence/` graph, contradiction, temporal reasoning and provenance
- `embeddings/` embedding generation
- `retrieval/` lexical, vector, graph and hybrid retrieval
- `rag/` context construction and answer verification
- `api/` FastAPI service
- `evaluation/` benchmark and metric modules
- `configs/` application configuration
- `tests/` automated tests
- `data/` local data directories (ignored by Git)

## Quick start (Python scaffold)

Python 3.11 is recommended.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# Linux / WSL:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env  # On Windows: Copy-Item .env.example .env
python -m evidence.processor --chunks data/processed/chunks.jsonl --output data/evidence
uvicorn api.main:app --reload
```

In a second terminal, start the React/Vite/Tailwind evidence workspace:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The UI talks to the local API, returns source
excerpts, and uses a grounded local Qwen answer when Ollama is running. The API
automatically falls back to source excerpts if the model is unavailable or returns
an answer with missing, invented, or unsupported citations. Current support validation accepts complete source sentences; paraphrases fall back to excerpts.

For student-friendly grounded answers, install Ollama and pull the configured model:

```bash
ollama pull qwen3:4b
ollama serve
```

## Current capabilities

- Ingest PDF, DOCX, PPTX, PPSX, TXT, and Markdown. The historical 83-document corpus is not present in this checkout; its final counts are unverified.
- Extract entities, candidate claims, candidate events, and explicit dependency-backed entity relationships.
- Validate every stored candidate against its document, chunk, path, and source offsets.
- Write JSONL evidence artifacts with deterministic IDs and a reproducible summary.
- Search source chunks through BM25 and expose documents, dashboard statistics, and investigations through FastAPI.
- Browse evidence in a responsive React/Vite/Tailwind frontend.

Evidence is deliberately labelled as candidate extractionâ€”not verified fact.

## Configuration

Copy `.env.example` to `.env` and fill in credentials locally. Never commit `.env`
or API keys.

## Development milestones

1. Ingestion and source provenance
2. Spark ETL and Parquet output
3. Claim/entity extraction
4. Evidence graph
5. Contradiction and temporal reasoning
6. BM25, vector search and RRF
7. Evidence-aware reranking
8. RAG and citation validation
9. Evaluation and dashboard

## Research integrity

Do not report placeholder metrics as results. Maintain labelled evaluation data,
record model versions and configuration, and compare all retrieval methods on the
same query set. Treat model confidence as an uncalibrated score until validated.

## Verification and remaining research work

See [the implementation checklist and reproducible commands](docs/IMPLEMENTATION_STATUS.md). Local fixture tests and frontend builds are verified separately from external model/database/cluster integrations and real-corpus research experiments. Do not interpret implemented adapters as measured research results.
