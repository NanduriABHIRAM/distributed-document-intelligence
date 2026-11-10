from rag.answer_generator import generate_answer
from rag.citation_validator import validate_citations


class GroundedClient:
    def chat(self, system: str, user: str) -> str:
        return "An operating system manages hardware resources. [E1]"


class UncitedClient:
    def chat(self, system: str, user: str) -> str:
        return "An operating system manages hardware resources."


def test_grounded_answer_is_accepted_with_known_citation(tmp_path):
    path = tmp_path / "source.txt"
    path.write_text("An operating system manages hardware resources.")
    evidence = [{"evidence_id":"E1", "text":path.read_text(), "source_path":str(path)}]
    result = generate_answer("What is an OS?", "[E1] source text", 1, client=GroundedClient(), evidence=evidence)
    assert result["mode"] == "ollama_grounded"
    assert result["citation_validation"]["valid"]


def test_uncited_model_answer_is_rejected_to_safe_fallback():
    result = generate_answer("What is an OS?", "[E1] source text", 1, client=UncitedClient())
    assert result["mode"] == "extractive_fallback"
    assert result["grounded"]


def test_unknown_citation_is_invalid():
    assert not validate_citations("An answer [E99]", {"E1"})["valid"]
