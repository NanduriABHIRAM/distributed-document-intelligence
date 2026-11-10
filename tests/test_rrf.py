from retrieval.rrf import reciprocal_rank_fusion

def test_rrf_combines_ranked_lists():
    lexical = [{"id": "a"}, {"id": "b"}]
    semantic = [{"id": "b"}, {"id": "c"}]
    result = reciprocal_rank_fusion([lexical, semantic])
    assert result[0]["id"] == "b"
    assert len(result) == 3


def test_rrf_retains_each_retriever_score_and_rank():
    lexical = [{"id": "a", "bm25_score": 3.2, "bm25_rank": 1}]
    semantic = [{"id": "a", "vector_score": 0.91, "vector_rank": 1}]
    result = reciprocal_rank_fusion([lexical, semantic])
    assert result[0]["bm25_score"] == 3.2
    assert result[0]["vector_score"] == 0.91
    assert result[0]["rrf_score"] > 0
