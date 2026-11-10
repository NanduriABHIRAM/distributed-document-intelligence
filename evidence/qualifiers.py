"""Keep uncertainty explicit; no publication-date substitution."""
import re

def qualifiers(text):
    modal = re.search(r'\b(may|might|could|would|possibly|perhaps|if)\b', text, re.I)
    attribution = re.search(r'\b(?:according to|reported by)\s+([^,.;]+)', text, re.I)
    scope = re.search(r'\b(?:in|across)\s+(India|Europe|Asia|the US|the UK)\b|\b(globally|worldwide)\b', text, re.I)
    date = re.search(r'\b(?:19|20)\d{2}(?:-\d{2}-\d{2})?\b', text)
    return dict(negated=bool(re.search(r"\b(no|not|never|without)\b|n't", text, re.I)),
                modality=modal.group(0).lower() if modal else None,
                attribution=attribution.group(1) if attribution else None,
                scope=scope.group(0).lower() if scope else None,
                event_date=date.group(0) if date else None,
                date_kind='explicit' if date else 'unknown')
