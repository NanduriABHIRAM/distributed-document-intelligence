"""Explicit temporal bounds; publication time is never substituted for event time."""
from datetime import date
import re

def temporal_bounds(claim):
    kind = claim.get('date_kind', 'unknown')
    if kind in ('inferred', 'publication'):
        return {'kind': kind, 'start': None, 'end': None}
    value = claim.get('valid_from') or claim.get('event_date')
    if not value:
        matches = re.findall(r'\b(?:19|20)\d{2}(?:-\d{2}-\d{2})?\b', claim.get('claim_text', ''))
        value = matches[0] if len(matches) == 1 else None
    def parse(value, end=False):
        if not value: return None
        value = str(value)
        try:
            if re.fullmatch(r'\d{4}', value):
                return date(int(value), 12 if end else 1, 31 if end else 1)
            return date.fromisoformat(value)
        except ValueError:
            return None
    start = parse(value)
    end = parse(claim.get('valid_to') or value, True)
    if start and end and start > end: start = end = None
    return {'kind': 'explicit' if start and end else 'unknown', 'start': start, 'end': end}

def compare_temporal_claims(claim_a, claim_b):
    a, b = temporal_bounds(claim_a), temporal_bounds(claim_b)
    if not all((a['start'], a['end'], b['start'], b['end'])):
        return {'relationship': 'unknown', 'reason': 'Missing, inferred, ambiguous or invalid event/validity dates.'}
    if a['start'] == b['start'] and a['end'] == b['end']:
        relation = 'same_period'
    elif max(a['start'], b['start']) <= min(a['end'], b['end']):
        relation = 'overlap'
    else:
        from evidence.contradiction_detector import classify_claim_pair
        label = classify_claim_pair(claim_a.get('claim_text',''), claim_b.get('claim_text',''))['label']
        relation = 'historical_update' if label == 'historical_update' else 'disjoint'
    return {'relationship': relation, 'reason': 'Compared explicit event/validity bounds, not publication dates.',
            'periods': [[a['start'].isoformat(), a['end'].isoformat()], [b['start'].isoformat(), b['end'].isoformat()]]}
