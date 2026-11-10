"""Optional cross-encoder; model loading happens only when explicitly configured."""
from functools import lru_cache
@lru_cache(maxsize=2)
def _model(name):
    from sentence_transformers import CrossEncoder
    return CrossEncoder(name)
def rerank(query, records, model_name, top_k=10):
    if not records: return []
    scores = _model(model_name).predict([(query,item['text']) for item in records])
    ranked = [{**item,'rerank_score':float(score)} for item,score in zip(records,scores)]
    return sorted(ranked,key=lambda item:item['rerank_score'],reverse=True)[:top_k]
