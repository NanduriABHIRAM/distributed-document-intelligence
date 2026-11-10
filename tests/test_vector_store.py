import numpy as np

from retrieval.vector_retriever import VectorRetriever


class FakeEmbedder:
    def encode(self, texts):
        values = {"alpha": [1.0, 0.0], "beta": [0.0, 1.0], "query": [1.0, 0.0]}
        return np.asarray([values[text] for text in texts], dtype=np.float32)


def test_vector_index_round_trips_with_chunk_mapping(tmp_path):
    retriever = VectorRetriever(embedder=FakeEmbedder())
    retriever.fit([{"chunk_id": "a", "text": "alpha"}, {"chunk_id": "b", "text": "beta"}])
    index_path, records_path = tmp_path / "chunks.faiss", tmp_path / "records.json"
    retriever.save(index_path, records_path, {"complete": True})
    loaded = VectorRetriever.load(index_path, records_path, FakeEmbedder())
    assert loaded.search("query", top_k=1)[0]["chunk_id"] == "a"
