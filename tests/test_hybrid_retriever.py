from retrieval.hybrid_retriever import HybridRetriever


class StaticRetriever:
    def __init__(self, results):
        self.results = results

    def search(self, query, top_k=100):
        return self.results[:top_k]


def test_hybrid_rrf_preserves_retrieval_provenance():
    lexical = StaticRetriever([{"id": "a", "chunk_id": "a", "bm25_score": 2.0}, {"id": "b", "chunk_id": "b", "bm25_score": 1.0}])
    dense = StaticRetriever([{"id": "b", "chunk_id": "b", "vector_score": 0.9}, {"id": "c", "chunk_id": "c", "vector_score": 0.8}])
    results, metadata = HybridRetriever(lexical, dense).search("test", top_k=3)
    assert metadata["mode"] == "hybrid_rrf"
    assert results[0]["id"] == "b"
    assert "rrf_score" in results[0]


def test_hybrid_degrades_to_bm25_when_dense_index_is_absent():
    lexical = StaticRetriever([{"id": "a", "chunk_id": "a", "bm25_score": 2.0}])
    results, metadata = HybridRetriever(lexical).search("test", top_k=1)
    assert metadata["mode"] == "bm25_only"
    assert results[0]["id"] == "a"
