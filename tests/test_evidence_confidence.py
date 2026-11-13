from api.routes.investigations import _retrieval_confidences


def test_evidence_confidence_is_normalized_to_the_best_result():
    assert _retrieval_confidences([{"rrf_score": 0.04}, {"rrf_score": 0.02}]) == [100, 50]


def test_evidence_confidence_handles_missing_or_zero_scores():
    assert _retrieval_confidences([{}, {}]) == [0, 0]
