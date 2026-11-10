"""Exact labelled evidence matching, including provenance."""
def extraction_report(predicted, expected):
    predicted,expected=set(predicted),set(expected)
    tp=len(predicted&expected)
    precision=tp/len(predicted) if predicted else 0.0
    recall=tp/len(expected) if expected else 0.0
    return {'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0.0,
            'true_positive':tp,'false_positive':len(predicted-expected),'false_negative':len(expected-predicted)}
def provenance_report(records, chunks):
    valid=0
    for record in records:
        s=record['source']; c=chunks.get(s['chunk_id']); a,b=s.get('start_offset'),s.get('end_offset')
        valid+=bool(c and s['document_id']==c['document_id'] and s['source_path']==c['source_path']
                    and s['source_text']==c['text'] and type(a)is int and type(b)is int and 0<=a<b<=len(c['text']))
    return {'records':len(records),'provenance_correctness':valid/len(records) if records else 0.0,
            'invalid_evidence_rate':sum(r.get('validation_status')=='INVALID' for r in records)/len(records) if records else 0.0}
