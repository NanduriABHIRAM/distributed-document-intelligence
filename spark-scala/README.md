# Spark + Scala chunk preparation

`DocumentETL` validates provenance, rejects duplicate IDs, repartitions the chunk corpus and writes Parquet on Spark executors. It does not claim to run NLP extraction in Scala. Run the validated Python ingestion/extraction pipeline first.

Prerequisites: compatible Java, sbt, Spark 3.5.1 and Scala 2.12.18. The job has not been compiled or executed in the current Windows environment because these runtimes are absent.

```powershell
cd spark-scala
sbt package
spark-submit --class DocumentETL --master "local[2]" target/scala-2.12/distributed-document-intelligence-etl_2.12-0.1.0.jar ../data/processed/chunks.jsonl ../data/spark-output 2
```

For a cluster, use shared storage paths and the cluster master URL. Output paths must not already exist. Compare the same input hash across `local[1]`, `local[2]` and the cluster. Run each setting repeatedly and retain the adjacent `-metrics` output. These measurements benchmark chunk preparation, not PDF parsing or NLP throughput. No distributed speedup is established until the experiment is run.
