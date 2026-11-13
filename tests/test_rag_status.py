import httpx

from rag.answer_generator import generate_answer
from rag.citation_validator import validate_citations
from rag.ollama_client import OllamaTimeoutError


def evidence(tmp_path, text="An operating system manages hardware resources."):
    source = tmp_path / "source.txt"
    source.write_text(text)
    return [{"evidence_id": "E1", "source_path": str(source), "text": text}]


def test_exact_citation_is_verified(tmp_path):
    result = validate_citations("An operating system manages hardware resources. [E1]", {"E1"}, evidence(tmp_path))
    assert result["valid"] and result["answer_status"] == "VERIFIED_EXACT"


def test_paraphrase_is_valid_but_not_semantically_verified(tmp_path):
    result = validate_citations("The operating system manages hardware. [E1]", {"E1"}, evidence(tmp_path))
    assert result["valid"] and result["answer_status"] == "CITATION_VALID_UNVERIFIED"
    assert result["semantic_entailment_verified"] is False


def test_citation_without_statement_and_uncited_tail_are_rejected(tmp_path):
    result = validate_citations("[E1] Extra assertion.", {"E1"}, evidence(tmp_path))
    assert not result["valid"]
    assert "Citation has no attached statement." in result["errors"]
    assert "Answer contains uncited trailing text." in result["errors"]


def test_multiple_citations_are_supported(tmp_path):
    items = evidence(tmp_path)
    second = tmp_path / "second.txt"
    second.write_text("Applications run on the operating system.")
    items.append({"evidence_id": "E2", "source_path": str(second), "text": second.read_text()})
    result = validate_citations("An operating system manages hardware resources. [E1] Applications run on the operating system. [E2]", {"E1", "E2"}, items)
    assert result["valid"] and result["citations"] == ["E1", "E2"]


def test_timeout_is_not_reported_as_connection_failure(tmp_path):
    class Client:
        def chat(self, *_):
            raise OllamaTimeoutError("too slow")
    result = generate_answer("What does it manage?", "[E1] source", 1, Client(), evidence(tmp_path))
    assert result["generation_failure"] == "timeout"


def test_http_timeout_is_handled(tmp_path):
    class Client:
        def chat(self, *_):
            raise httpx.TimeoutException("too slow")
    result = generate_answer("What does it manage?", "[E1] source", 1, Client(), evidence(tmp_path))
    assert result["generation_failure"] == "timeout"


def test_qwen_thinking_trace_is_not_returned_to_the_citation_validator(monkeypatch):
    from rag.ollama_client import OllamaClient
    response = httpx.Response(200, request=httpx.Request("POST", "http://ollama.test/api/chat"),
                              json={"message": {"content": "<think>private trace</think>\nA cited answer. [E1]"}})
    monkeypatch.setattr("rag.ollama_client.httpx.post", lambda *_, **__: response)
    assert OllamaClient().chat("system", "user") == "A cited answer. [E1]"


def test_qwen_trace_without_opening_tag_is_removed(monkeypatch):
    from rag.ollama_client import OllamaClient
    response = httpx.Response(200, request=httpx.Request("POST", "http://ollama.test/api/chat"),
                              json={"message": {"content": "private trace</think>\nA cited answer. [E1]"}})
    monkeypatch.setattr("rag.ollama_client.httpx.post", lambda *_, **__: response)
    assert OllamaClient().chat("system", "user") == "A cited answer. [E1]"
