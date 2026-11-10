"""JSONL loading and transactional PostgreSQL evidence persistence."""
import json
from pathlib import Path
KINDS = {'entities':'entity_id','claims':'claim_id','events':'event_id','relationships':'relationship_id'}
def records(path):
    path = Path(path)
    if not path.exists(): return
    with path.open(encoding='utf-8') as source:
        for line in source:
            if line.strip(): yield json.loads(line)

def import_postgres(directory, dsn):
    import psycopg
    from psycopg.types.json import Jsonb
    totals = {}
    with psycopg.connect(dsn) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS evidence_records (kind text NOT NULL, id text NOT NULL, document_id text NOT NULL, chunk_id text NOT NULL, payload jsonb NOT NULL, PRIMARY KEY(kind,id))')
        conn.execute('CREATE INDEX IF NOT EXISTS evidence_chunk_idx ON evidence_records(chunk_id)')
        for kind, id_field in KINDS.items():
            totals[kind] = 0
            for record in records(Path(directory)/f'{kind}.jsonl'):
                source = record['source']
                conn.execute('INSERT INTO evidence_records VALUES (%s,%s,%s,%s,%s) ON CONFLICT(kind,id) DO UPDATE SET document_id=EXCLUDED.document_id, chunk_id=EXCLUDED.chunk_id, payload=EXCLUDED.payload',
                             (kind,record[id_field],source['document_id'],source['chunk_id'],Jsonb(record)))
                totals[kind] += 1
    return totals

if __name__ == '__main__':
    import argparse
    from configs.runtime import option
    parser=argparse.ArgumentParser(); parser.add_argument('--evidence',default='data/evidence')
    args=parser.parse_args()
    dsn=option('storage','postgres_dsn',None,'POSTGRES_DSN')
    if not dsn: parser.error('Set POSTGRES_DSN')
    print(json.dumps(import_postgres(args.evidence,dsn),indent=2))
