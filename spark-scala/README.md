# Spark + Scala ETL

This module is reserved for distributed extraction, cleaning, normalization,
chunking and Parquet output.

Suggested initial job:
1. Read a manifest of document paths and metadata.
2. Distribute processing across Spark partitions.
3. Produce rows containing document_id, chunk_id, text, page/slide, offsets,
   source_path and processing metadata.
4. Write partitioned Parquet output.

Use the Scala/Spark versions compatible with your installed Java and Spark runtime.
Record exact versions in the experiment log.
