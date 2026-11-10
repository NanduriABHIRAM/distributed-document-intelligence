class GraphRetriever:
    def __init__(self, evidence_graph):
        self.evidence_graph = evidence_graph

    def expand(self, claim_ids: list[str]) -> list[dict]:
        return self.evidence_graph.expand_claim_evidence(claim_ids)
