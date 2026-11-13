# TraceRAG final project walkthrough

## Project responsibilities

TraceRAG connects document extraction to evidence-based retrieval. The frontend
offers document questions, a separate RAG workspace, OCR previews, an evidence
explorer, and an interactive graph. The Python API handles the live RAG workflow.
Scala/Spark provides the distributed data processing and independently queryable
lexical retrieval implementation.

```text
Documents / scans
      |
Python loaders + optional OCR -> chunks.jsonl -> Python NLP evidence JSONL
      |                              |                    |
      |                              +---------+----------+
      |                                        |
      |                              Scala / Spark pipeline
      |                              - quality + quarantine
      |                              - corpus analytics
      |                              - BM25 index + search
      |                              - evidence source joins
      |                              - graph degrees + PageRank
      |                              - timeline + review groups
      |                                        |
      |                              Parquet datasets + metrics
      |
Python hybrid retriever -> cited answer -> React RAG / evidence UI
```

The Scala outputs are available for inspection and standalone search. They do
not silently replace the Python API's retrieval index. This distinction makes
the implemented integration and its boundaries clear during a demonstration.

## Suggested demonstration

1. Run the frontend and API using the root README. Open the RAG Workspace and
   show retrieval counts, model readiness, answers, and source citations.
2. Open OCR, upload a digital PDF or a scan, and inspect page text. Scans need
   Tesseract English language data; OCR previews are downloaded for subsequent
   ingestion and are not automatically indexed.
3. Open Evidence Graph. Filter entities, select a node, and inspect highlighted
   neighbors and source references.
4. Build Scala with `sbt test package`. Run the six-chunk demo from
   `spark-scala/README.md`. Inspect quality, document, partition, and duplicate
   content datasets.
5. Run `tracerag.SearchIndex` for `research laboratory`. Explain term frequency,
   inverse document frequency, chunk-length normalization, and source joins.
6. Inspect graph degrees and PageRank. Show the explicit-date timeline and the
   two revenue claims flagged for review. Do not call review groups verified
   contradictions or PageRank a confidence score.
7. Show the Scala tests and metrics. Describe local execution honestly; demonstrate
   a multi-worker deployment only if you actually run one.

## Delivery contents

The source archive contains Python backend and ingestion/retrieval modules,
React source and production assets, Scala source/tests/demo/build files, configs,
requirements, and documentation. When built, the Scala JAR is included under
`spark-scala/target/scala-2.12/`. Runtime installations, dependency caches,
personal documents, `.env`, and generated research data are excluded.

Reinstall dependencies on a new machine. The root Python requirements and
frontend package manifest specify the dependencies; sbt resolves Scala/Spark
dependencies. Java 17 and Spark 3.5.1 are needed for the Scala runtime. Model and
OCR dependencies are optional until the corresponding features are used.
