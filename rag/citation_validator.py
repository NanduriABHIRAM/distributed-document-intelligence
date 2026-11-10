"""Exact source sentence validation; paraphrases require review, not automatic trust."""
import re
from pathlib import Path

def validate_citations(answer: str, allowed_source_ids: set[str], evidence=None) -> dict:
    citations = set(re.findall(r'\[([A-Za-z]\w*)\]', answer))
    errors = [f'Unknown citation: {c}' for c in sorted(citations - allowed_source_ids)]
    if not citations:
        errors.append('The generated answer contains no evidence citations.')
    if evidence is None:
        errors.append('Source evidence is required to verify support.')
    else:
        sources = {item['evidence_id']: item for item in evidence}
        cursor = 0
        for match in re.finditer(r'((?:\[[A-Za-z]\w*\]\s*)+)', answer):
            statement = answer[cursor:match.start()].strip().strip('"')
            ids = re.findall(r'\[([A-Za-z]\w*)\]', match.group())
            if not statement:
                errors.append('Citation has no attached statement.')
            for cid in ids:
                source = sources.get(cid)
                if source is None:
                    errors.append(f'{cid} was not retrieved.')
                    continue
                if not Path(source.get('source_path', '')).is_file():
                    errors.append(f'{cid} source file is missing.')
                expected_hash = source.get('metadata', {}).get('sha256')
                if expected_hash and Path(source.get('source_path', '')).is_file():
                    from ingestion.utils import sha256_file
                    if sha256_file(Path(source['source_path'])) != expected_hash:
                        errors.append(f'{cid} source file changed since ingestion.')
                text = source.get('text', '').strip()
                sentences = re.split(r'(?<=[.!?])\s+', text)
                if statement not in sentences and statement != text:
                    errors.append(f'{cid} does not support a complete source statement.')
            cursor = match.end()
        if answer[cursor:].strip():
            errors.append('Answer contains uncited trailing text.')
    return {'valid': not errors, 'citations': sorted(citations), 'errors': errors,
            'method': 'exact_source_sentence', 'semantic_entailment_verified': False}
