"""Evaluate human-reviewed claim pairs and answers from JSONL annotations."""
import argparse
import json
from pathlib import Path
from evidence.store import records
from evidence.contradiction_detector import classify_claim_pair
from evidence.temporal_reasoner import compare_temporal_claims
from evaluation.contradiction_metrics import classification_report
from evaluation.temporal_metrics import temporal_report
from evaluation.answer_metrics import groundedness_rate
from ingestion.utils import sha256_file

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--labels',required=True); parser.add_argument('--output',required=True)
    args=parser.parse_args(); rows=list(records(args.labels))
    if not rows or any(not r.get('reviewed') for r in rows): parser.error('Nonempty human-reviewed labels required')
    pairs=[r for r in rows if r['kind']=='claim_pair']; answers=[r for r in rows if r['kind']=='answer']
    result={'labels_sha256':sha256_file(Path(args.labels))}
    if pairs:
        result['contradiction']=classification_report([classify_claim_pair(r['a']['claim_text'],r['b']['claim_text'])['label'] for r in pairs],[r['expected_label'] for r in pairs])
        result['temporal']=temporal_report([compare_temporal_claims(r['a'],r['b'])['relationship'] for r in pairs],[r['expected_temporal'] for r in pairs])
    if answers:
        result['answers']={key:groundedness_rate([r[key] for r in answers]) for key in ('grounded','relevant','citations_correct')}
    Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
if __name__=='__main__': main()
