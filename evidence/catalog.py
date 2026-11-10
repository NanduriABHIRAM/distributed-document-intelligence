"""Load only valid evidence tied to the current chunk corpus."""
from pathlib import Path
from evidence.store import records, KINDS
from evidence.evidence_graph import EvidenceGraph
from evidence.contradiction_detector import classify_claim_pair
from evidence.temporal_reasoner import compare_temporal_claims
from itertools import combinations

def build_graph(chunks, directory, driver=None):
    graph=EvidenceGraph(driver)
    for chunk in chunks: graph.add_chunk(chunk)
    loaded={}
    for kind in KINDS:
        loaded[kind]=[]
        for record in records(Path(directory)/f'{kind}.jsonl'):
            source=record['source']; chunk=graph.chunks.get(source['chunk_id'])
            if (record.get('validation_status')=='VALID' and chunk and
                source['document_id']==chunk['document_id'] and source['source_text']==chunk['text'] and
                source['source_path']==chunk['source_path']): loaded[kind].append(record)
    for kind, method in [('entities',graph.add_entity),('claims',graph.add_claim),('events',graph.add_event)]:
        for record in loaded[kind]: method(record)
    graph.link_evidence(loaded['relationships'])
    return graph

def analyze(graph, chunk_ids, max_pairs=500):
    claims=[r for r in graph.claims.values() if r['source']['chunk_id'] in chunk_ids]
    output=[]; checked=0
    for a,b in combinations(claims,2):
        if (a.get('subject') or '').casefold()!=(b.get('subject') or '').casefold() or a.get('predicate')!=b.get('predicate'): continue
        if checked>=max_pairs: break
        checked+=1
        result=classify_claim_pair(a['claim_text'],b['claim_text'])
        if result['label']!='neutral':
            output.append({**result,'claim_ids':[a['claim_id'],b['claim_id']],
                           'sources':[a['source'],b['source']], 'temporal':compare_temporal_claims(a,b)})
    return {'comparisons':output,'pairs_checked':checked,'pair_limit':max_pairs,
            'truncated':checked>=max_pairs,'claims_available':len(claims)}
