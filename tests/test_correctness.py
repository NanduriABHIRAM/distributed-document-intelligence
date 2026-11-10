"""Regression cases from the handoff and the audit."""
from dataclasses import asdict
import json
import pytest
from evidence.contradiction_detector import classify_claim_pair
from evidence.temporal_reasoner import compare_temporal_claims
from rag.citation_validator import validate_citations
from evaluation.retrieval_metrics import ndcg_at_k, recall_at_k

@pytest.mark.parametrize('a,b,label', [
 ('The product was released in 2023.','The product was released in 2024.','contradiction'),
 ('The company had 100 employees in 2022.','The company had 250 employees in 2025.','historical_update'),
 ('The company has 100 employees in India.','The company has 500 employees globally.','scope_difference'),
 ('The company may launch a product next year.','The company launched a product.','uncertain'),
 ('Alice is ready.','Bob is not ready.','neutral'),
 ('Alice is ready.','Alice is not ready.','contradiction'),
 ('The company had 100 employees in 2022.','The company had 250 employees in 2022.','contradiction'),
])
def test_claim_semantics(a,b,label):
    assert classify_claim_pair(a,b)['label']==label

def test_publication_is_not_event_time():
    assert compare_temporal_claims({'publication_date':'2025'}, {'event_date':'2025'})['relationship']=='unknown'
    assert compare_temporal_claims({'event_date':'2025','date_kind':'inferred'}, {'event_date':'2025'})['relationship']=='unknown'

def test_intervals_and_invalid_dates():
    assert compare_temporal_claims({'valid_from':'2020','valid_to':'2025'}, {'event_date':'2023'})['relationship']=='overlap'
    assert compare_temporal_claims({'event_date':'2025-99-99'}, {'event_date':'2025'})['relationship']=='unknown'

@pytest.mark.parametrize('answer,valid', [
 ('The company did not acquire LinkedIn. [E1]',True),
 ('The company acquired LinkedIn. [E1]',False),
 ('The Moon is made of cheese. [E1]',False),
 ('The company did not acquire LinkedIn. [E1] Unsupported extra claim.',False),
 ('The company did not acquire LinkedIn. [E9]',False),
 ('The company did not acquire LinkedIn.',False),
])
def test_support_requires_exact_complete_source(tmp_path,answer,valid):
    p=tmp_path/'source.txt'; p.write_text('The company did not acquire LinkedIn.')
    evidence=[dict(evidence_id='E1',text=p.read_text(),source_path=str(p))]
    assert validate_citations(answer,{'E1'},evidence)['valid']==valid

def test_missing_source_rejected():
    assert not validate_citations('A fact. [E1]',{'E1'},[dict(evidence_id='E1',text='A fact.',source_path='missing-file')])['valid']

def test_metrics_duplicate_and_graded():
    assert recall_at_k(['a','a'],{'a','b'},2)==0.5
    assert ndcg_at_k(['a','b'],{'a':2,'b':1},2)==1
    assert ndcg_at_k(['b','a'],{'a':2,'b':1},2)<1

def test_document_identity_and_chunk_provenance(tmp_path):
    from ingestion.text_loader import load_text
    from ingestion.chunking import chunk_section
    a=tmp_path/'one'/'report.txt'; b=tmp_path/'two'/'report.txt'
    a.parent.mkdir(); b.parent.mkdir(); a.write_text('The same report.'); b.write_text('The same report.')
    left,right=load_text(a),load_text(b)
    assert left.document_id!=right.document_id
    assert load_text(a).document_id==left.document_id
    c=chunk_section(left.sections[0],left)[0]
    assert left.sections[0].text[c.start_offset:c.end_offset]==c.text

def test_relationship_cooccurrence_cannot_be_valid():
    from evidence.schemas import SourceReference, EvidenceEntity, EvidenceRelationship
    from evidence.evidence_validator import validate_relationships
    text='Microsoft and LinkedIn are mentioned.'
    chunk=dict(document_id='d',chunk_id='c',source_path='s',text=text)
    def source(a,b): return SourceReference('d','c','s',text,start_offset=a,end_offset=b)
    entities=[EvidenceEntity('a','Microsoft','microsoft','ORG',source(0,9),'test'),
              EvidenceEntity('b','LinkedIn','linkedin','ORG',source(14,22),'test')]
    r=EvidenceRelationship('r','a','b','ACQUIRE',source(0,len(text)),True)
    assert validate_relationships(chunk,[r],entities)[0].validation_status!='VALID'

def test_graph_cross_document_expansion():
    from evidence.evidence_graph import EvidenceGraph
    g=EvidenceGraph()
    for i in (1,2):
        g.add_chunk(dict(chunk_id=str(i),document_id='d'+str(i),source_path='s',text='Microsoft'))
        g.add_entity(dict(entity_id='e'+str(i),normalized_text='microsoft',entity_type='ORG',
                          source=dict(chunk_id=str(i),start_offset=0,end_offset=9)))
    assert g.expand_chunks(['1'])[0]['chunk_id']=='2'

def test_index_resume_rejects_changed_model(tmp_path):
    from retrieval.vector_retriever import VectorRetriever
    import numpy as np
    class FakeEmbedder:
        def encode(self, texts): return np.asarray([[1.,0.] for _ in texts],dtype=np.float32)
    r=VectorRetriever(embedder=FakeEmbedder()); r.fit([dict(chunk_id='a',text='alpha')])
    r.save(tmp_path/'a.faiss',tmp_path/'a.json',{'embedding_model':'old-model'})
    with pytest.raises(ValueError,match='model'):
        VectorRetriever.load(tmp_path/'a.faiss',tmp_path/'a.json',FakeEmbedder())

def test_retrieval_runner_requires_reviewed_labels():
    from evaluation.run_retrieval import evaluate
    with pytest.raises(ValueError,match='reviewed'):
        evaluate([dict(query_id='q',query='test',relevance={})],{})


def test_changed_source_cannot_be_cited(tmp_path):
    from ingestion.utils import sha256_file
    p=tmp_path/'source'; p.write_text('An original sentence.')
    evidence=[dict(evidence_id='E1',text=p.read_text(),source_path=str(p),metadata={'sha256':sha256_file(p)})]
    p.write_text('The document was replaced.')
    assert not validate_citations('An original sentence. [E1]',{'E1'},evidence)['valid']
