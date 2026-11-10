from retrieval.rrf import reciprocal_rank_fusion

def test_rrf_combines_ranked_lists():
    lexical = [{"id": "a"}, {"id": "b"}]
    semantic = [{"id": "b"}, {"id": "c"}]
    result = reciprocal_rank_fusion([lexical, semantic])
    assert result[0]["id"] == "b"
    assert len(result) == 3
