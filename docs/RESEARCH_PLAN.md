# Research Plan

## Working research title
Evidence-Centric Hybrid Retrieval for Distributed Document Intelligence with
Contradiction Detection and Temporal Reasoning.

## Research questions
- RQ1: Does graph-enhanced retrieval improve evidence retrieval over BM25, vector,
  and conventional RRF baselines?
- RQ2: Does temporal reasoning reduce false contradiction labels for historical updates?
- RQ3: Does evidence-aware retrieval improve answer groundedness and citation quality?
- RQ4: How does Spark processing scale with document volume and worker configuration?

## Baselines
1. BM25
2. Dense vector retrieval
3. BM25 + vector using RRF
4. RRF + graph evidence expansion
5. RRF + graph evidence expansion + temporal-aware reranking

## Required labels
- Query-to-relevant-chunk judgments
- Claim-pair relationship: contradiction, entailment/support, neutral
- Temporal relationship: update, overlap, disjoint, unknown
- Source provenance and page/paragraph references

## Metrics
Retrieval: Precision@K, Recall@K, MRR, nDCG@K.
Contradiction: precision, recall, macro-F1, confusion matrix.
Temporal: interval extraction accuracy and relation classification F1.
Answers: correctness, groundedness, citation precision and completeness.
BDA: processing time, throughput, memory, partition scaling and speedup.

## Experimental safeguards
- Use the same query set for all retrieval baselines.
- Split by document/source where possible to avoid leakage.
- Tune thresholds on validation data, not test data.
- Report confidence intervals and paired significance tests.
- Do not treat NLI probabilities or LLM self-confidence as calibrated confidence.
- Keep genuine contradictions separate from historical updates.
