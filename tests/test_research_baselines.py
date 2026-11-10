from evaluation.contradiction_metrics import classification_report
from evaluation.temporal_metrics import temporal_report
from evidence.claim_matcher import find_candidate_claim_pairs
from evidence.contradiction_detector import classify_claim_pair
from evidence.evidence_graph import EvidenceGraph
from evidence.temporal_reasoner import compare_temporal_claims


def test_temporal_difference_is_an_update_not_a_conflict():
    result = compare_temporal_claims(
        {"claim_text": "The company had 100 employees in 2022."},
        {"claim_text": "The company had 250 employees in 2025."},
    )
    assert result["relationship"] == "historical_update"
    assert classify_claim_pair("The company had 100 employees in 2022.", "The company had 250 employees in 2025.")["label"] == "historical_update"


def test_claim_pairing_and_in_memory_graph():
    claims = [
        {"claim_id": "a", "subject": "OpenAI", "predicate": "release", "claim_text": "OpenAI released GPT four."},
        {"claim_id": "b", "subject": "OpenAI", "predicate": "release", "claim_text": "OpenAI released GPT four."},
    ]
    assert find_candidate_claim_pairs(claims) == [("a", "b")]
    graph = EvidenceGraph()
    graph.add_document({"document_id": "doc"})
    graph.add_claim({**claims[0], "source": {"document_id": "doc", "chunk_id": "chunk"}})
    assert graph.expand_claim_evidence(["a"])[0]["graph_relation"] == "requested"


def test_evaluation_reports_are_computed():
    assert temporal_report(["same_period", "historical_update"], ["same_period", "historical_update"])["accuracy"] == 1.0
    report = classification_report(["contradiction", "neutral"], ["contradiction", "neutral"])
    assert report["macro_f1"] == 1.0
