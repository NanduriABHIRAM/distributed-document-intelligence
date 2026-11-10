"""Evidence graph adapter with an in-memory baseline and optional Neo4j persistence."""

from __future__ import annotations


class EvidenceGraph:
    def __init__(self, driver=None):
        self.driver = driver
        self.documents: dict[str, dict] = {}
        self.claims: dict[str, dict] = {}

    def add_document(self, document: dict) -> None:
        document_id = document["document_id"]
        self.documents[document_id] = dict(document)
        if self.driver is not None:
            with self.driver.session() as session:
                session.run("MERGE (d:Document {document_id: $document_id}) SET d += $document", document_id=document_id, document=document)

    def add_claim(self, claim: dict) -> None:
        claim_id = claim["claim_id"]
        self.claims[claim_id] = dict(claim)
        if self.driver is not None:
            document_id = claim.get("source", {}).get("document_id") or claim.get("document_id")
            with self.driver.session() as session:
                session.run(
                    "MERGE (c:Claim {claim_id: $claim_id}) SET c += $claim "
                    "WITH c MATCH (d:Document {document_id: $document_id}) "
                    "MERGE (d)-[:CONTAINS_CLAIM]->(c)",
                    claim_id=claim_id, claim=claim, document_id=document_id,
                )

    def expand_claim_evidence(self, claim_ids: list[str]) -> list[dict]:
        requested = [self.claims[claim_id] for claim_id in claim_ids if claim_id in self.claims]
        source_chunks = {claim.get("source", {}).get("chunk_id") for claim in requested}
        evidence = []
        for claim in self.claims.values():
            source = claim.get("source", {})
            if claim.get("claim_id") in claim_ids or source.get("chunk_id") in source_chunks:
                record = dict(claim)
                record["id"] = record["claim_id"]
                record["graph_relation"] = "requested" if record["claim_id"] in claim_ids else "same_chunk_context"
                evidence.append(record)
        return evidence
