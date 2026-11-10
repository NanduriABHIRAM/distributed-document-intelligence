"""End-to-end tests on generated fixtures, never the research corpus."""
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import pytest

@pytest.fixture
def corpus(tmp_path):
    import pymupdf as fitz
    from docx import Document
    from pptx import Presentation
    from pptx.util import Inches
    raw=tmp_path/'raw'; raw.mkdir()
    text='Microsoft acquired LinkedIn in 2016.'
    (raw/'plain.txt').write_text(text,encoding='utf-8')
    (raw/'notes.md').write_text('# Acquisition\n'+text,encoding='utf-8')
    doc=Document(); doc.add_paragraph(text); doc.save(raw/'word.docx')
    pdf=fitz.open(); page=pdf.new_page(); page.insert_text((72,72),text); pdf.save(raw/'paper.pdf'); pdf.close()
    slides=Presentation(); slide=slides.slides.add_slide(slides.slide_layouts[6]); slide.shapes.add_textbox(Inches(1),Inches(1),Inches(7),Inches(1)).text=text
    slides.save(raw/'slides.pptx')
    with ZipFile(raw/'slides.pptx') as source, ZipFile(raw/'show.ppsx','w',ZIP_DEFLATED) as target:
        for item in source.infolist():
            data=source.read(item.filename)
            if item.filename=='[Content_Types].xml':
                data=data.replace(b'presentationml.presentation.main+xml',b'presentationml.slideshow.main+xml')
            target.writestr(item,data)
    return raw

def test_all_formats_to_validated_graph(corpus,tmp_path):
    import pyarrow.parquet as pq
    from ingestion.pipeline import run_pipeline
    from evidence.processor import process_evidence
    from evidence.catalog import build_graph
    from evidence.store import records
    processed=tmp_path/'processed'; evidence=tmp_path/'evidence'
    summary=run_pipeline(corpus,processed,parquet=True)
    assert summary['discovered']==summary['succeeded']==6
    assert summary['failed']==0
    chunks=list(records(processed/'chunks.jsonl'))
    assert pq.read_table(processed/'chunks.parquet').num_rows==len(chunks)
    assert len({c['document_id'] for c in chunks})==6
    result=process_evidence(processed/'chunks.jsonl',evidence,batch_size=2)
    assert result['chunks']==len(chunks) and result['invalid']==0
    assert result['relationships']>=5
    assert result['complete'] and result['model_version']
    graph=build_graph(chunks,evidence)
    assert graph.entities and graph.claims and graph.events
    assert any(e['type']=='RELATED_TO' for e in graph.edges)

def test_query_pipeline_includes_conflict_analysis(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from api.main import app
    import api.routes.investigations as route
    from evidence.evidence_graph import EvidenceGraph
    source=tmp_path/'source.txt'; source.write_text('The product was released in 2023.')
    chunks=[dict(chunk_id=str(i),document_id='doc'+str(i),source_path=str(source),file_type='txt',text=f'The product was released in {year}.') for i,year in enumerate((2023,2024))]
    graph=EvidenceGraph()
    for c in chunks:
        graph.add_chunk(c)
        graph.add_claim(dict(claim_id=c['chunk_id'],subject='product',predicate='release',claim_text=c['text'],source={**c,'source_text':c['text']}))
    monkeypatch.setattr(route,'search_chunks',lambda q,k:(chunks,{'mode':'test'}))
    monkeypatch.setattr(route,'get_graph',lambda:graph)
    monkeypatch.setattr(route,'generate_answer',lambda *a,**kw:{'answer':'fixture','grounded':False,'mode':'test'})
    response=TestClient(app).post('/investigations/query',json={'query':'When was the product released?'})
    assert response.status_code==200
    result=response.json()
    assert result['conflicts'][0]['label']=='contradiction'
    assert len(result['evidence'])==2

def test_model_refuses_unsupported_known_citation(tmp_path):
    from rag.answer_generator import generate_answer
    p=tmp_path/'source'; p.write_text('The company did not acquire LinkedIn.')
    class Client:
        def chat(self,*args): return 'The company acquired LinkedIn. [E1]'
    result=generate_answer('What happened?','context',1,Client(),[dict(evidence_id='E1',source_path=str(p),text=p.read_text())])
    assert result['mode']=='extractive_fallback'

def test_negation_and_hypothetical_relations_are_not_asserted():
    from evidence.entity_extractor import load_nlp, extract_entities
    from evidence.relationship_extractor import extract_relationships
    nlp=load_nlp()
    for text in ['Microsoft did not acquire LinkedIn.','Microsoft may acquire LinkedIn.','If Microsoft acquired LinkedIn, Google would respond.']:
        c=dict(document_id='d',chunk_id='c',source_path='s',text=text)
        assert extract_relationships(c,extract_entities(c,nlp),nlp)==[]


def test_failed_processing_preserves_previous_outputs(tmp_path):
    from evidence.processor import process_evidence
    path=tmp_path/'chunks.jsonl'; path.write_text('{invalid json')
    out=tmp_path/'evidence'; out.mkdir()
    (out/'claims.jsonl').write_text('previous output')
    with pytest.raises(json.JSONDecodeError): process_evidence(path,out)
    assert (out/'claims.jsonl').read_text()=='previous output'
