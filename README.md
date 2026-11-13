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

## Quick start

Python 3.11 is recommended.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# Linux / WSL:
source .venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env  # On Windows: Copy-Item .env.example .env
# Place your input documents in data/raw before ingestion.
python -m ingestion.cli --input data/raw --output data/processed --parquet
python -m evidence.processor --chunks data/processed/chunks.jsonl --output data/evidence
uvicorn api.main:app --reload
```

To check file discovery without processing, run
`python -m ingestion.cli --input data/raw --scan-only`. Ingestion prints progress
for every file and saves `summary.json`, `failures.json`, and `warnings.json` in
the output folder. Mixed PDFs retain readable pages when OCR is unavailable;
skipped pages are reported in `warnings.json`. Entirely unreadable documents are
reported as failures, and a run with no usable passages preserves the old corpus.

In a second terminal, start the React/Vite/Tailwind evidence workspace:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The UI includes an Evidence Graph backed by validated
JSONL records and an answer path that distinguishes exact quotations from cited
paraphrases. The API falls back to source passages if generation fails or a citation
is missing, invented, or unsupported. Paraphrases are shown as citation-valid but
semantic support remains explicitly unverified unless an NLI verifier is added.

For student-friendly grounded answers, install Ollama and pull the configured model:

```bash
ollama pull qwen3:4b
ollama pull bge-m3
ollama serve
```

Useful graph API endpoints are `GET /graph`, `GET /graph/stats`,
`GET /graph/entities/{entity_id}`, `GET /graph/relationships/{relationship_id}` and
`POST /graph/rebuild`. Spark status is available at `GET /spark/status`; `POST
/spark/run` starts the configured local Spark job asynchronously only after its JAR
has been built.

## Scala implementation and final project

The Scala/Spark implementation includes typed input schemas, reason-coded data
quality checks, corpus and partition analytics, a distributed BM25 inverted index
and search CLI, evidence/source integrity joins, explicit-date timelines, claim
review groups, graph degrees, and iterative PageRank.

- [Scala build, demo, algorithms, and output reference](spark-scala/README.md)
- [Final project architecture and presentation walkthrough](docs/FINAL_PROJECT.md)
- [Recorded validation results](docs/VALIDATION.md)

Build with `sbt test package` from `spark-scala` using Java 17. The existing Spark
API launch command remains compatible. Run `python scripts/package_project.py`
from the repository root to create the source/demo/JAR archive in `releases/`.

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
# RAG workspace, OCR, and graph navigation

The web UI includes a **RAG Workspace** tab with corpus/model readiness, a
3–20 passage retrieval selector, cited answers, and retrieval diagnostics.
It uses the same investigation endpoint as Ask Documents.

The **OCR** tab accepts PDF, PNG, and JPEG files up to 20 MB and 50 pages.
Automatic mode preserves embedded text and recognizes pages without text;
force mode recognizes every page. Review the page previews and download a
text file, then ingest that file through the existing ingestion workflow.
Preview uploads are not persisted or automatically indexed. PDF ingestion
also uses OCR for pages without embedded text.

OCR requires Tesseract English language data on the API/ingestion host.
Install Tesseract and set `TESSDATA_PREFIX` to the directory containing
`eng.traineddata` before starting the API or ingestion command. Digital PDF
text extraction works without it; scans return an actionable setup error
when the language data is unavailable.

In **Evidence Graph**, select an entity to highlight its neighboring entities
and inspect relationships in the side panel. Labels appear for selected
relationships and the selected entity's connections. Use zoom, scrolling,
or dragging to explore larger graphs, and Reset to restore the pan/zoom.
