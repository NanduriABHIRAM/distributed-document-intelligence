# Handoff implementation and verification

Checked on 2026-11-10. This is an implementation checklist, not a claim that research objectives have been demonstrated.

| Requirement | Implementation | Verification |
|---|---|---|
| Six document formats including PPSX | Complete loaders and in-memory slideshow normalization | Generated fixtures passed |
| Cleaning, overlap, stable IDs, source provenance | Implemented; IDs include absolute path and content hash | Collision and offset regression tests passed |
| JSONL and Parquet | Streaming JSONL and bounded Arrow batches | Mixed-format round trip passed |
| Entities, claims, events, relationships | spaCy dependency/NER baselines with qualifiers | Fixture extraction passed; quality on real corpus pending |
| Evidence builder and validator | Schema/span/reference checks; dependency support rechecked; uncertain relationships excluded | Regression tests passed; VALID means source-supported candidate, not independently verified fact |
| Batch processor and summaries | Shared NLP parse, staged writes, model/version/input hash and invalid/review counts | End-to-end and failure-preservation tests passed |
| BM25 / embeddings / FAISS / RRF | Implemented; model and corpus mismatch guards | Lexical, synthetic-vector persistence and fusion tests passed; BGE-M3 live run pending |
| Evidence graph | Document, Chunk, Entity, Claim, Event nodes; source-bearing edges; bounded graph traversal | In-memory and mocked Neo4j contract tests passed; live Neo4j pending |
| Graph retrieval | Connected to API; exact name/type mention matching labelled as assumption | Cross-document fixture passed; entity disambiguation remains a research limitation |
| Cross-encoder | Configurable, lazy-loaded reranker | Adapter implemented; actual model evaluation pending |
| Temporal and contradiction analysis | Conservative rules and explicit validity intervals; connected to API/UI | Handoff examples passed; broad NLP accuracy not established |
| Grounded generation | Qwen/Ollama adapter, evidence context, fallback | Mocked generation and source support tests passed; live Qwen pending |
| Citation validation | Exact complete source sentences, retrieved IDs, existing files, optional source hash | Hallucination/negation/missing/stale-source tests passed; paraphrases deliberately rejected |
| PostgreSQL | Transactional JSONB evidence importer with provenance keys | Implemented; live server integration pending |
| FastAPI and React/Vite/Tailwind | Retrieval, evidence, candidate conflict and temporal display | API fixture and frontend production build passed |
| Spark/Scala | Distributed validation, repartitioning and Parquet preparation job | Source added; compilation and cluster execution pending (runtimes absent) |
| Research metrics | Precision/Recall/MRR/nDCG, extraction PRF, provenance, answer/temporal/conflict metrics | Metric regressions passed |
| E1-E5 / multilingual / scalability experiments | Shared-judgment runner, label runner and resource benchmark command | Not run: corpus, reviewed labels and external services unavailable |
| Reproducibility/configuration | YAML plus environment settings; Python environment lock; input hashes and experiment arguments | Dependency consistency check passed |

## Compatibility and migration

Evidence schema version 2 adds optional negation, modality, attribution, scope and temporal fields. Existing field names remain intact. Regenerate chunks because document identity now includes source path and file content. Regenerate evidence and FAISS after ingestion; do not mix old smoke artifacts with the new corpus. Moving a corpus changes its identities. Chunk offsets refer to cleaned section text; evidence offsets refer to chunk text. Parquet stores heterogeneous metadata as a JSON string.

VALID evidence is a structurally and syntactically supported extraction candidate, never a certified real-world fact. Contradiction scores are rule outputs, not calibrated probabilities. Exact-sentence citation validation verifies source reproduction, not the truth of the source. The temporal baseline abstains on unsupported relative/inferred dates. Cross-language retrieval depends on BGE-M3 and requires labelled Hindi/Telugu evaluations; the English spaCy extractor is not a multilingual extraction model.

## Reproduce local verification

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe -m pip check
cd frontend
npm ci
npm run build
```

Tests generate isolated fixtures; they never create a purported research corpus. Database adapter mocks do not substitute for live database integration tests.

## Run the real corpus when available

```powershell
.venv/Scripts/python.exe -m ingestion.cli --input data/raw --output data/processed --parquet
.venv/Scripts/python.exe -m evidence.processor --chunks data/processed/chunks.jsonl --output data/evidence
ollama pull bge-m3
ollama pull qwen3:4b
.venv/Scripts/python.exe -m retrieval.build_vector_index
.venv/Scripts/python.exe -m uvicorn api.main:app --reload
```

Review `summary.json` and `failures.json`; a failed or missing document must not be counted as successful. Review extraction candidates manually before reporting precision/recall. Ingestion and index construction are offline jobs: stop the API while publishing a new corpus, then restart it. Multi-file output publication is staged but not one database transaction. Concurrent writers are not supported.

## Optional databases

Set POSTGRES_PASSWORD, POSTGRES_DSN and NEO4J_PASSWORD in your local `.env`. Match the DSN to the Compose database/user (`docintel`). Then:

```powershell
docker compose up -d
.venv/Scripts/python.exe -m evidence.store --evidence data/evidence
.venv/Scripts/python.exe -m evidence.sync_graph --chunks data/processed/chunks.jsonl --evidence data/evidence
```

The API uses a corpus-scoped in-memory graph; Neo4j persistence is an explicit import. Its bounded traversal uses the same evidence representation. PostgreSQL is an optional persistence sink, not the default API data source. Imports upsert IDs; use a separate database for a different corpus to avoid retaining historical rows unintentionally.

## Research experiments

Create JSONL judgments with `query_id`, `query`, `language`, `relevance` (chunk ID to nonnegative grade) and `reviewed: true` only after actual human review. Include English-to-Hindi and English-to-Telugu cases. Keep one frozen query set for all methods and separate development/test documents.

```powershell
.venv/Scripts/python.exe -m evaluation.run_retrieval --queries data/evaluation/queries.jsonl --chunks data/processed/chunks.jsonl --index data/processed/chunks.faiss --records data/processed/chunks.vectors.json --evidence data/evidence --reranker cross-encoder/ms-marco-MiniLM-L-6-v2 --output data/evaluation/retrieval-results.json
.venv/Scripts/python.exe -m evaluation.run_labels --labels data/evaluation/reviewed-labels.jsonl --output data/evaluation/label-results.json
```

Without dense/graph/reranker inputs, unavailable experiments are explicitly counted; they are not simulated. Label rows use `kind: claim_pair`, `a`/`b` claim dictionaries, `expected_label`, `expected_temporal`, and `reviewed`; answer rows use `kind: answer` with human-assigned `grounded`, `relevant`, `citations_correct` booleans. Extraction metrics accept exact annotation keys (include document/chunk/span/type). No labelled evaluation corpus has been invented.

Use `python -m evaluation.benchmark --items N --output run.json -- <command>` for timed command measurements. The report records return code, sampled process-tree CPU and peak RSS; GPU use is explicitly unmeasured. See `spark-scala/README.md` for distributed preparation. Compare identical input hashes and repeated runs; do not report a speedup until measured.

## Remaining work requiring external resources

- Restore and process the original 83-document corpus; verify final failures, Parquet and evidence outputs.
- Run real BGE-M3, cross-encoder and Qwen models and measure quality, latency and GPU use.
- Verify Neo4j and PostgreSQL against live servers.
- Compile/run the Scala job with the documented runtime versions, then benchmark a cluster.
- Build a human-reviewed research set and run E1-E5, multilingual, extraction, answer and scalability experiments.
- Expand conservative language rules/models based on measured failures. General semantic correctness is not guaranteed by passing fixtures.
