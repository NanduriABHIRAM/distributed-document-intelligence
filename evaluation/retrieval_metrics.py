"""Rank metrics with duplicate protection and graded nDCG."""
import math

def _ranked(retrieved,k):
    if k<1: raise ValueError('k must be positive')
    return list(dict.fromkeys(retrieved))[:k]
def precision_at_k(retrieved,relevant,k):
    return len(set(_ranked(retrieved,k)) & relevant)/k
def recall_at_k(retrieved,relevant,k):
    ranked=_ranked(retrieved,k)
    return len(set(ranked)&relevant)/len(relevant) if relevant else 0.0
def reciprocal_rank(retrieved,relevant):
    return next((1/r for r,item in enumerate(dict.fromkeys(retrieved),1) if item in relevant),0.0)
def ndcg_at_k(retrieved, relevance, k):
    ranked=_ranked(retrieved,k)
    if any(v<0 for v in relevance.values()): raise ValueError('Relevance must be nonnegative')
    dcg=sum((2**relevance.get(item,0)-1)/math.log2(rank+1) for rank,item in enumerate(ranked,1))
    ideal=sum((2**grade-1)/math.log2(rank+1) for rank,grade in enumerate(sorted(relevance.values(),reverse=True)[:k],1))
    return dcg/ideal if ideal else 0.0
