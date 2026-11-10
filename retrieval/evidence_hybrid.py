from retrieval.rrf import reciprocal_rank_fusion

def evidence_hybrid_search(query: str, bm25, vector, graph, top_k: int = 10) -> list[dict]:
    lexical = bm25.search(query, top_k=100)
    semantic = vector.search(query, top_k=100) if vector is not None else []
    fused = reciprocal_rank_fusion([lexical, semantic] if semantic else [lexical])
    if graph is None:
        return fused[:top_k]
    claim_ids = [item.get("claim_id") for item in fused[:top_k] if item.get("claim_id")]
    expansion = graph.expand(claim_ids) if claim_ids else []
    known = {item["id"] for item in fused}
    contextual = [item for item in expansion if item.get("id") not in known]
    return (fused + contextual)[:top_k]
