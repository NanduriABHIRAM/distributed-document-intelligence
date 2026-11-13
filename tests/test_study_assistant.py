import json

from rag.study_assistant import _json_object, generate_study_answer


def _evidence(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("An operating system manages computer hardware resources.")
    return [{"evidence_id": "E1", "source_path": str(source), "text": source.read_text()}]


def test_study_answer_accepts_json_wrapped_in_model_prose(tmp_path):
    payload = {
        "document_answer": "An operating system manages computer hardware resources. [E1]",
        "general_answer": "",
    }

    class Client:
        def chat(self, *_):
            return f"Here is the JSON you requested:\n```json\n{json.dumps(payload)}\n```"

    result = generate_study_answer("What does an operating system manage?", _evidence(tmp_path), [], client=Client())
    assert result["document_answer"] == payload["document_answer"]


def test_json_object_keeps_only_the_first_json_value():
    assert _json_object('Note: {"document_answer":"a","general_answer":""} Thanks.') == '{"document_answer":"a","general_answer":""}'


def test_study_answer_returns_a_cited_passage_when_model_declines_evidence(tmp_path):
    class Client:
        def chat(self, *_):
            return '{"document_answer":"","general_answer":""}'

    result = generate_study_answer("What is an operating system?", _evidence(tmp_path), [], client=Client())
    assert result["citation_status"] == "extractive_document_fallback"
    assert "[E1]" in result["document_answer"]
    assert "manages computer hardware resources" in result["document_answer"]


def test_study_answer_falls_back_when_model_invents_a_citation(tmp_path):
    class Client:
        def chat(self, *_):
            return '{"document_answer":"An OS manages resources. [E99]","general_answer":""}'

    result = generate_study_answer("What is an operating system?", _evidence(tmp_path), [], client=Client())
    assert result["citation_status"] == "extractive_document_fallback"
    assert "[E1]" in result["document_answer"]
