# Validation record — 13 November 2026

## Scala build and tests

- Compiled all eight main Scala source files with Scala 2.12.18 and Spark 3.5.1.
- Built `distributed-document-intelligence-etl_2.12-0.1.0.jar`.
- **11 Scala tests passed**, running Spark `local[2]` under Java 17 on Windows.
- Tested CLI validation, malformed records, provenance offsets, duplicate IDs,
  duplicate content, numerical BM25 scores, Unicode retrieval, empty indexes,
  source mismatches, dangling relationships, PageRank normalization, isolated
  nodes, explicit dates, and claim review labels.

## Full Scala demo

Executed the built application through SparkSubmit under Java 17 in Ubuntu WSL,
using the checked-in synthetic demo and `local[2]`, two output partitions, and
three PageRank iterations. This was local execution, not a multi-worker cluster.

Persisted outputs were checked by `spark-scala/scripts/verify_demo.py`:

| Check | Observed result |
| --- | --- |
| Chunks / source documents | 6 / 3 |
| Accepted entities / relationships | 4 / 2 |
| Rejected chunks / evidence | 0 / 0 |
| Duplicate-content groups | 1, containing 2 chunks |
| Explicit timeline events | 1 |
| Claim review groups | 1 |
| PageRank sum | 1 within floating-point tolerance |
| Endpoint references | All exported endpoints exist |
| BM25 index statistics | 6 retrieval chunks |

The Scala search CLI loaded the persisted index and searched `research laboratory`.
It returned `c3`, `c4`, `c5`, then `c0`, with scores approximately 1.151808,
1.102757, 1.102757, and 0.411753, together with document IDs, paths, and text.

The observed ETL run took approximately 51.8 seconds in this development/WSL
environment, including many small Parquet publications. This tiny fixture is a
correctness test, not a throughput benchmark or evidence of cluster speedup.

## Python and frontend

**15 selected Python tests passed** across Spark API control, OCR, graph API,
health, and ingestion/evidence integration. Pytest used a project-local temporary
directory because the existing system pytest directory had Windows ACL issues.

The frontend production build passed during the preceding RAG/OCR/graph UI work.
This Scala expansion does not change frontend source. Real scan recognition still
requires external Tesseract English language data; mocked OCR and digital-PDF
extraction tests do not constitute an installed Tesseract runtime test.

## Scope of verification

No multi-node deployment, production load test, model-quality benchmark, or
full-corpus research evaluation is claimed. The existing personal/research corpus
is excluded from the release archive. Dependency caches and Java runtimes used
for verification are also excluded; follow the documented runtime setup on a
new machine.
