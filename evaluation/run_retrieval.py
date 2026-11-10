"""Run E1-E5 on the same reviewed JSONL judgments; never substitute missing methods."""
import argparse
import json
import time
import platform
from pathlib import Path
from evaluation.retrieval_metrics import precision_at_k, recall_at_k, reciprocal_rank, ndcg_at_k
from evidence.store import records
from ingestion.utils import sha256_file

def evaluate(queries, methods, k=10):
    rows=[]
    for query in queries:
        if not query.get('reviewed'): raise ValueError('Each judgment must be manually reviewed')
        relevant={key for key,value in query['relevance'].items() if value>0}
        for name, search in methods.items():
            start=time.perf_counter(); results=search(query['query'],k); elapsed=time.perf_counter()-start
            ids=[r.get('chunk_id',r.get('id')) for r in results]
            rows.append({'query_id':query['query_id'],'language':query.get('language','unspecified'),'experiment':name,
                         'precision_at_k':precision_at_k(ids,relevant,k),'recall_at_k':recall_at_k(ids,relevant,k),
                         'reciprocal_rank':reciprocal_rank(ids,relevant),'ndcg_at_k':ndcg_at_k(ids,query['relevance'],k),
                         'latency_ms':elapsed*1000,'ranking':ids})
    metrics=['precision_at_k','recall_at_k','reciprocal_rank','ndcg_at_k','latency_ms']
    summary={name:{metric:sum(r[metric] for r in rows if r['experiment']==name)/len(queries) for metric in metrics}
             for name in methods} if queries else {}
    return {'k':k,'queries':len(queries),'summary':summary,'results':rows}

def main():
    from retrieval.bm25_retriever import BM25Retriever
    from retrieval.vector_retriever import VectorRetriever
    from retrieval.ollama_client import OllamaEmbedder
    from retrieval.hybrid_retriever import HybridRetriever
    from retrieval.rrf import reciprocal_rank_fusion
    from retrieval.reranker import rerank
    from evidence.catalog import build_graph
    parser=argparse.ArgumentParser()
    parser.add_argument('--queries',required=True); parser.add_argument('--chunks',required=True)
    parser.add_argument('--index'); parser.add_argument('--records'); parser.add_argument('--evidence')
    parser.add_argument('--reranker'); parser.add_argument('--output',required=True); parser.add_argument('--k',type=int,default=10)
    args=parser.parse_args(); chunks=list(records(args.chunks)); queries=list(records(args.queries))
    if not chunks or not queries: parser.error('Nonempty corpus and reviewed queries are required')
    known={c['chunk_id'] for c in chunks}
    if any(set(q['relevance'])-known for q in queries): parser.error('Judgments reference chunks outside this corpus')
    lexical=BM25Retriever(); lexical.fit(chunks); methods={'E1_BM25':lexical.search}
    if args.index and args.records:
        metadata=json.loads(Path(args.records).with_suffix('.meta.json').read_text())
        if not metadata.get('complete') or metadata.get('chunks_sha256')!=sha256_file(Path(args.chunks)):
            parser.error('Dense index is incomplete or belongs to another corpus')
        dense=VectorRetriever.load(args.index,args.records,OllamaEmbedder())
        hybrid=HybridRetriever(lexical,dense)
        methods.update(E2_Dense=dense.search,E3_RRF=lambda q,k:hybrid.search(q,k)[0])
        if args.evidence:
            graph=build_graph(chunks,args.evidence)
            def expanded(q,k):
                base=hybrid.search(q,max(100,k))[0]
                extra=graph.expand_chunks([r['chunk_id'] for r in base[:k]])
                return reciprocal_rank_fusion([base,extra])[:k]
            methods['E4_Graph']=expanded
            if args.reranker: methods['E5_Reranked']=lambda q,k:rerank(q,expanded(q,100),args.reranker,k)
    result=evaluate(queries,methods,args.k)
    result['configuration']=vars(args)
    result['corpus_sha256']=sha256_file(Path(args.chunks)); result['judgments_sha256']=sha256_file(Path(args.queries))
    result['python']=platform.python_version(); result['unavailable_experiments']=5-len(methods)
    path=Path(args.output); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(result,indent=2),encoding='utf-8')
if __name__=='__main__': main()
