"""Conservative, explainable candidate conflict detection (not verified facts)."""
import re
from evidence.qualifiers import qualifiers

def _normal(text):
    return ' '.join(re.findall(r"[\w']+", text.casefold()))

def classify_claim_pair(claim_a: str, claim_b: str) -> dict:
    left, right = _normal(claim_a), _normal(claim_b)
    qa, qb = qualifiers(claim_a), qualifiers(claim_b)
    def result(label, reason):
        return dict(label=label, reason=reason, needs_review=label == 'contradiction',
                    evidence=[claim_a, claim_b], method='conservative_rules',
                    entailment=float(label == 'entails'), contradiction=float(label == 'contradiction'),
                    neutral=float(label not in ('entails', 'contradiction')))
    if qa['modality'] or qb['modality']:
        return result('uncertain', 'A conditional or modal statement is not a confirmed event.')
    if qa['attribution'] != qb['attribution']:
        return result('attribution_difference', 'Statements have different or unknown attributions.')
    if qa['scope'] != qb['scope']:
        return result('scope_difference', 'Geographic scopes differ or are not both explicit.')
    if left == right:
        return result('entails', 'Identical normalized statements, not independent fact verification.')
    if qa['negated'] and qb['negated']:
        return result('neutral', 'Two negative statements with different values need semantic review.')
    # Require matching wording apart from values; shared words alone prove nothing.
    skeleton = lambda text: re.sub(r'\b\d+(?:[.,]\d+)*\b', '#', text)
    if skeleton(left) == skeleton(right):
        years_a = re.findall(r'\b(?:19|20)\d{2}\b', left)
        years_b = re.findall(r'\b(?:19|20)\d{2}\b', right)
        if years_a != years_b and years_a and years_b:
            if re.search(r'\b(released|launched|founded|acquired|born|died)\b', left):
                return result('contradiction', 'Different dates asserted for an otherwise matching event; identity needs review.')
            if re.search(r'\b(employees|revenue|population|members|users)\b', left):
                return result('historical_update', 'Matching changing quantity measured in different years.')
            return result('neutral', 'Different dates without enough evidence to identify update or conflict.')
        return result('contradiction', 'Different values in otherwise matching statements with compatible scope/time.')
    remove_negation = lambda text: ' '.join(re.sub(r"\b(not|never)\b", '', text).split())
    if qa['negated'] != qb['negated'] and remove_negation(left) == remove_negation(right):
        return result('contradiction', 'Same statement with opposing explicit negation.')
    return result('neutral', 'Insufficient aligned evidence; semantic review required.')
