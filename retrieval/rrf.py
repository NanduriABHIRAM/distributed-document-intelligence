def reciprocal_rank_fusion(result_lists: list[list[dict]], k: int = 60) -> list[dict]:
    scores = {}
    records = {}
    for results in result_lists:
        for rank, item in enumerate(results, start=1):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            # Merge instead of replacing: a fused result must retain the lexical
            # and dense scores/ranks needed for evaluation and provenance.
            records[item_id] = {**records.get(item_id, {}), **item}
    fused = []
    for item_id, score in scores.items():
        record = dict(records[item_id])
        record["rrf_score"] = score
        fused.append(record)
    return sorted(fused, key=lambda x: x["rrf_score"], reverse=True)
