# Scala distributed document intelligence

Scala is responsible for distributed data quality, corpus analytics, lexical
retrieval, evidence integrity, and graph analytics. Python handles document/OCR
extraction, NLP, embedding retrieval, and answer generation. The Scala index is
independently queryable; the interactive Python RAG endpoint continues to use
its existing retriever.

## Build and run

Use Java **17**, sbt **1.10.7**, Spark **3.5.1**, and Scala **2.12.18**.
Spark libraries are `provided`: submit the application JAR through Spark rather
than executing it with `java -jar`. Linux/WSL is recommended for running the file
pipeline. Native Windows Spark file writes require compatible Hadoop native tools.

```sh
cd spark-scala
sbt test package
spark-submit --class DocumentETL --master 'local[2]' \
  target/scala-2.12/distributed-document-intelligence-etl_2.12-0.1.0.jar \
  demo/chunks.jsonl demo-output/run-001 2 demo/evidence --pagerank-iterations=5

spark-submit --class tracerag.SearchIndex --master 'local[2]' \
  target/scala-2.12/distributed-document-intelligence-etl_2.12-0.1.0.jar \
  demo-output/run-001 'research laboratory' 5
```

On PowerShell, use the equivalent single-line commands or `./scripts/run-demo.ps1`.
The checked-in demo has six synthetic chunks, four entity mentions, two
relationships, two differing claims, and one explicitly dated event.
`python scripts/generate_demo.py` regenerates it without external dependencies.
After running the demo, verify its saved datasets with
`python scripts/verify_demo.py demo-output/run-001` (requires the root Python
environment's `pyarrow` dependency).

For the real corpus, replace the demo input with `../data/processed/chunks.jsonl`
and the evidence directory with `../data/evidence`. Omit the evidence argument
to build corpus analytics and BM25 only. Existing `POST /spark/run` launches this
same `DocumentETL` entry point; `GET /spark/status` exposes state and metrics.
The API saves subprocess output to `logs/spark-job.log`.

## Implementation map

| Scala module | Implemented responsibility |
| --- | --- |
| `DocumentETL` | Job orchestration, Parquet publication, caching, completion metrics, output collision protection |
| `JobConfig` | Validated CLI configuration; optional quarantine and bounded PageRank iterations |
| `Schemas` | Explicit chunk/entity/relationship/claim/event contracts, nested provenance, corrupt JSON capture |
| `ChunkQuality` | Required fields, offset/text alignment, duplicate IDs, normalized content fingerprints, reason-coded quarantine |
| `CorpusAnalytics` | Document sizes, formats, source sections, actual partition distribution and skew |
| `LexicalIndex` / `SearchIndex` | Unicode tokenization, inverted postings, term/document frequencies, IDF, BM25 ranking, persisted-index query CLI |
| `EvidenceAnalytics` | Corpus reference joins, source consistency, duplicate evidence IDs, graph endpoint validation, entity mentions, explicit-date timeline, claim review candidates |
| `GraphAnalytics` | Provenance-preserving node/edge exports, in/out degrees, iterative PageRank with dangling-node redistribution |

## Output datasets

Each suffix below is appended to the output prefix. Every dataset is Parquet
except `-metrics`, which is a JSON directory for compatibility with the API.

| Output | Contents |
| --- | --- |
| `<prefix>` | Valid chunks, original text and offsets, derived normalized text and SHA-256 content hash |
| `-quality`, `-invalid-chunks` | Counts by rejection reason; rejected input rows (second output only when needed) |
| `-documents`, `-formats`, `-partitions` | Corpus summaries and actual partition distribution |
| `-duplicate-content` | Repeated content groups; source identities are retained |
| `-postings`, `-terms`, `-index-statistics` | BM25 inverted index and corpus statistics |
| `-entities`, `-relationships`, `-claims`, `-events` | Accepted evidence records |
| `-rejected-*` | Evidence rejected by source/ID/endpoint checks, with reasons |
| `-entity-mentions`, `-document-entities` | Cross-document entity summaries and document/entity mappings |
| `-timeline` | Events with explicit dates, retaining qualifiers and provenance |
| `-claim-review` | Groups with differing assertions that require human review |
| `-graph-nodes`, `-graph-edges` | Evidence graph, with original source references |
| `-graph-degrees`, `-graph-pagerank` | Structural graph statistics and ranked entity mentions |
| `-metrics` | Accepted/rejected counts, elapsed time, throughput, partitions, master, Spark version |

Example inspection in `spark-shell`:

```scala
spark.read.parquet("demo-output/run-001-claim-review").show(false)
spark.read.parquet("demo-output/run-001-graph-pagerank").orderBy($"pagerank".desc).show(false)
spark.read.parquet("demo-output/run-001-partitions").show(false)
spark.read.json("demo-output/run-001-metrics").show(false)
```

## Correctness rules

- Strict mode writes diagnostics and fails if any chunk is invalid. Add
  `--quarantine` to continue with valid chunks. An entirely invalid corpus fails.
- All copies of a repeated chunk/evidence ID are rejected; choosing an arbitrary
  row would make provenance nondeterministic.
- Duplicate **content** is reported, not discarded: two documents may legitimately
  quote the same passage. Chunk character totals include overlapping chunks and
  must not be reported as unique source-document length.
- A `VALID` upstream label is insufficient: evidence document, path, chunk, and
  source text must match an accepted chunk. Relationships must reference accepted
  entities from the same source chunk. Rejections remain inspectable.
- Claim groups are review candidates, not proven contradictions. Scope, modality,
  attribution, and event date remain part of the grouping key.
- PageRank ranks entity **mentions**, not globally resolved real-world entities.
  It collapses parallel endpoint pairs only for ranking; exports retain every
  accepted relationship and provenance. Iterations are fixed, not a convergence
  claim. Default damping is 0.85; the empty graph returns an empty ranking.
- Outputs never overwrite an existing prefix. On failure, partial datasets may
  remain for diagnosis; choose a fresh prefix for a retry. A metrics directory is
  published last and denotes completion. The set of directories is not an atomic
  transaction; use unique prefixes per concurrent job.

## Algorithm and scaling notes

For a query term `t` in chunk `d`, the score is:

```text
idf(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
score(t,d) = idf(t) * tf(t,d) * (k1 + 1)
             / (tf(t,d) + k1 * (1 - b + b * length(d) / avgLength))
```

Defaults are `k1=1.2`, `b=0.75`. Repeated query tokens count once. Results use
chunk ID as a deterministic tie-breaker. Tokenization preserves Unicode letters,
combining marks, and digits; this is a lexical baseline, not stemming or semantic
retrieval. Index operations use Spark joins and aggregations, not a driver-side
map of the corpus. PageRank uses local checkpoints to bound query-plan growth.
Local checkpoints are not fault-tolerant durable checkpoints.

For a cluster demonstration, submit the same JAR to the real cluster master and
use shared storage paths. Run identical inputs with different partition counts,
retain metrics and input hashes, and report measured results. Local threads do
not establish multi-node speedup. Large per-entity/claim `collect_set` groups and
hub-heavy graphs can still be skewed; monitor the Spark UI and partition report.

## Tests and presentation

`PipelineSpec` exercises malformed input, offsets, ID/content duplication, BM25
numeric correctness, Unicode and empty retrieval, source mismatches, graph
integrity, PageRank probability mass, isolated nodes, explicit dates, and claim
review labeling. Start your presentation with the demo, inspect Parquet outputs,
run the standalone Scala search command, and then show the implementation modules.
See `../docs/FINAL_PROJECT.md` for the full project walkthrough.
