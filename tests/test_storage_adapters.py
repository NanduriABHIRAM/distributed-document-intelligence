"""Adapter contracts without pretending a database server was exercised."""
from evidence.evidence_graph import EvidenceGraph

def test_neo4j_serializes_nested_sources_and_attaches_provenance():
    calls=[]
    class Session:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def run(self,query,**parameters):
            calls.append((query,parameters)); return self
        def consume(self): return None
    class Driver:
        def session(self): return Session()
    graph=EvidenceGraph(Driver())
    graph.add_chunk(dict(chunk_id='c',document_id='d',source_path='s',text='A fact.'))
    graph.add_claim(dict(claim_id='claim',claim_text='A fact.',source={'chunk_id':'c','document_id':'d'}))
    props=[p['props'] for _,p in calls if 'props' in p]
    assert all(not isinstance(v,dict) for p in props for v in p.values())
    assert any('SUPPORTS' in q and p['eid']=='claim' for q,p in calls)

def test_small_bm25_corpus_still_returns_exact_match():
    from retrieval.bm25_retriever import BM25Retriever
    r=BM25Retriever(); r.fit([dict(chunk_id='a',text='Microsoft acquired LinkedIn.')])
    assert r.search('Microsoft')[0]['chunk_id']=='a'
