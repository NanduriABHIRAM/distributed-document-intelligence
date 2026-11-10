"""Bounded-memory ingestion with atomic JSONL publication and batch Parquet output."""
from pathlib import Path
from dataclasses import asdict
import json
import time
import os
from .loaders import discover_documents, load_document
from .chunking import chunk_section

def run_pipeline(input_dir: Path, output_dir: Path, chunk_size=1200, overlap=150, parquet=False):
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    if not input_dir.is_dir(): raise FileNotFoundError(f'Input directory does not exist: {input_dir}')
    if chunk_size < 1 or not 0 <= overlap < chunk_size: raise ValueError('Invalid chunk size/overlap')
    paths = discover_documents(input_dir)
    if not paths: raise ValueError('No supported documents found; refusing to publish an empty corpus')
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary = output_dir / 'chunks.jsonl.tmp'
    failures=[]; successes=0; count=0; started=time.perf_counter()
    with temporary.open('w',encoding='utf-8') as stream:
        for path in paths:
            # Document loading fails before any chunks are committed.
            try:
                document=load_document(path)
                index=0
                for section in document.sections:
                    batch=chunk_section(section,document,chunk_size,overlap,index)
                    for chunk in batch: stream.write(json.dumps(asdict(chunk),ensure_ascii=False)+'\n')
                    index+=len(batch); count+=len(batch)
                successes+=1
            except Exception as error:
                failures.append({'source_path':str(path),'error':f'{type(error).__name__}: {error}'})
    os.replace(temporary,output_dir/'chunks.jsonl')
    if parquet:
        import pyarrow as pa
        import pyarrow.parquet as pq
        schema=pa.schema([
            ('chunk_id',pa.string()),('document_id',pa.string()),('source_path',pa.string()),
            ('file_type',pa.string()),('text',pa.string()),('start_offset',pa.int64()),('end_offset',pa.int64()),
            ('location_type',pa.string()),('location_number',pa.int64()),('chunk_index',pa.int64()),
            ('token_estimate',pa.int64()),('metadata',pa.string())])
        writer=None
        try:
            with (output_dir/'chunks.jsonl').open(encoding='utf-8') as source:
                batch=[]
                def write(batch):
                    nonlocal writer
                    # Metadata remains JSON to accommodate heterogeneous document formats.
                    rows=[{**r,'metadata':json.dumps(r['metadata'],ensure_ascii=False)} for r in batch]
                    table=pa.Table.from_pylist(rows, schema=schema)
                    if writer is None: writer=pq.ParquetWriter(output_dir/'chunks.parquet.tmp',table.schema)
                    writer.write_table(table)
                for line in source:
                    batch.append(json.loads(line))
                    if len(batch)>=512: write(batch); batch=[]
                if batch: write(batch)
        finally:
            if writer: writer.close()
        if writer: os.replace(output_dir/'chunks.parquet.tmp',output_dir/'chunks.parquet')
    elapsed=time.perf_counter()-started
    summary={'discovered':len(paths),'succeeded':successes,'failed':len(failures),'chunks':count,
             'elapsed_seconds':elapsed,'documents_per_second':successes/elapsed,'chunks_per_second':count/elapsed,
             'schema_version':2,'chunk_size':chunk_size,'overlap':overlap,'parquet':parquet,
             'offset_basis':'cleaned_section','document_id_scheme':'absolute_path_and_content_sha256'}
    (output_dir/'failures.json').write_text(json.dumps(failures,indent=2),encoding='utf-8')
    (output_dir/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary
