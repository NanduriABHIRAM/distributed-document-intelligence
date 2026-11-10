"""Explicit Neo4j import; local query graphs also work without a server."""
import argparse
from neo4j import GraphDatabase
from configs.runtime import option
from evidence.catalog import build_graph
from evidence.store import records

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--chunks',default='data/processed/chunks.jsonl')
    parser.add_argument('--evidence',default='data/evidence'); args=parser.parse_args()
    uri=option('storage','neo4j_uri','bolt://localhost:7687','NEO4J_URI')
    user=option('storage','neo4j_username','neo4j','NEO4J_USERNAME')
    password=option('storage','neo4j_password',None,'NEO4J_PASSWORD')
    if not password: parser.error('Set NEO4J_PASSWORD')
    with GraphDatabase.driver(uri,auth=(user,password)) as driver:
        driver.verify_connectivity()
        graph=build_graph(records(args.chunks),args.evidence,driver)
        print({'chunks':len(graph.chunks),'claims':len(graph.claims),'entities':len(graph.entities),'events':len(graph.events),'edges':len(graph.edges)})
if __name__=='__main__': main()
