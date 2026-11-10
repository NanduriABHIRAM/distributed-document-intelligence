"""Provenance-carrying evidence graph, with optional Neo4j persistence."""
from collections import defaultdict
import json

class EvidenceGraph:
    def __init__(self, driver=None):
        self.driver = driver
        self.documents, self.chunks, self.entities, self.claims, self.events = {}, {}, {}, {}, {}
        self.edges = []
        self.adj = defaultdict(set)

    def _node(self, kind, key, record):
        if self.driver is not None:
            # Nested source dictionaries are serialized, not illegal Neo4j property maps.
            props = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                     for k, v in record.items() if v is not None}
            with self.driver.session() as session:
                session.run(f'MERGE (n:{kind} {{id: $id}}) SET n += $props', id=key, props=props).consume()

    def _edge(self, source_kind, source_id, target_kind, target_id, relation, evidence):
        edge = dict(source=source_id, target=target_id, type=relation, evidence=evidence)
        self.edges.append(edge)
        self.adj[(source_kind, source_id)].add((target_kind, target_id))
        self.adj[(target_kind, target_id)].add((source_kind, source_id))
        if self.driver is not None:
            with self.driver.session() as session:
                session.run(f'MATCH (a:{source_kind} {{id:$a}}), (b:{target_kind} {{id:$b}}) '
                            f'MERGE (a)-[r:{relation} {{evidence_id:$eid}}]->(b) SET r.source=$source',
                            a=source_id, b=target_id, eid=evidence.get('evidence_id',''),
                            source=json.dumps(evidence, ensure_ascii=False)).consume()

    def add_document(self, document):
        key = document['document_id']; self.documents[key] = dict(document)
        self._node('Document', key, document)

    def add_chunk(self, chunk):
        key = chunk['chunk_id']; self.chunks[key] = dict(chunk)
        self.add_document({'document_id':chunk['document_id'], 'source_path':chunk['source_path']})
        self._node('Chunk', key, chunk)
        self._edge('Document',chunk['document_id'],'Chunk',key,'CONTAINS',{'chunk_id':key})

    def add_claim(self, claim):
        key = claim['claim_id']; self.claims[key] = dict(claim)
        self._node('Claim', key, claim)
        source = claim.get('source', {})
        if source.get('chunk_id') in self.chunks:
            self._edge('Chunk', source['chunk_id'], 'Claim', key, 'SUPPORTS', {**source,'evidence_id':key})

    def add_entity(self, entity):
        key = entity['entity_id']; self.entities[key] = dict(entity)
        self._node('Entity', key, entity)
        source = entity['source']
        self._edge('Chunk',source['chunk_id'],'Entity',key,'MENTIONS',{**source,'evidence_id':key})

    def add_event(self, event):
        key = event['event_id']; self.events[key] = dict(event)
        self._node('Event',key,event)
        self._edge('Chunk',event['source']['chunk_id'],'Event',key,'SUPPORTS',{**event['source'],'evidence_id':key})

    def link_evidence(self, relationships):
        # Span overlap establishes reference, not an inferred semantic relationship.
        by_chunk = defaultdict(list)
        for eid, entity in self.entities.items(): by_chunk[entity['source']['chunk_id']].append((eid, entity))
        for kind, records in [('Claim',self.claims), ('Event',self.events)]:
            for key, record in records.items():
                source = record.get('source',{})
                for eid, entity in by_chunk[source.get('chunk_id')]:
                    span = entity['source']
                    if (source.get('chunk_id') == span.get('chunk_id') and
                        source.get('start_offset',0) <= span.get('start_offset',-1) and
                        span.get('end_offset',-1) <= source.get('end_offset',-1)):
                        self._edge(kind,key,'Entity',eid,'REFERS_TO' if kind=='Claim' else 'INVOLVES',
                                   {**source,'evidence_id':key})
        for r in relationships:
            if r.get('validation_status') != 'VALID': continue
            if r['source_entity_id'] in self.entities and r['target_entity_id'] in self.entities:
                self._edge('Entity',r['source_entity_id'],'Entity',r['target_entity_id'],'RELATED_TO',
                           {**r['source'],'evidence_id':r['relationship_id'],'predicate':r['relationship_type']})

    def expand_chunks(self, chunk_ids, hops=2, limit=100):
        if not 1 <= hops <= 4: raise ValueError('hops must be between 1 and 4')
        frontier = {('Chunk', key) for key in chunk_ids}
        seen = set(frontier)
        # Conservative exact normalized entity names connect mentions across documents.
        names = defaultdict(set)
        for key, entity in self.entities.items():
            names[(entity['entity_type'],entity['normalized_text'])].add(('Entity',key))
        for _ in range(hops):
            following = set()
            for node in frontier:
                following.update(n for n in self.adj[node] if n[0] != 'Document')
                if node[0] == 'Entity':
                    e = self.entities[node[1]]
                    for alias in names[(e['entity_type'],e['normalized_text'])]:
                        following.update(n for n in self.adj[alias] if n[0] == 'Chunk')
            frontier = following - seen; seen.update(frontier)
        found = sorted(key for kind,key in seen if kind=='Chunk' and key not in chunk_ids)
        return [{**self.chunks[key], 'id':key, 'graph_relation':'shared_evidence_entity',
                 'graph_identity_assumption':'exact_name_and_type', 'graph_seed_chunks':list(chunk_ids)}
                for key in found[:limit] if key in self.chunks]

    def expand_claim_evidence(self, claim_ids):
        chunks = {self.claims[k].get('source',{}).get('chunk_id') for k in claim_ids if k in self.claims}
        chunks.discard(None)
        return [{**record,'id':key,'graph_relation':'requested' if key in claim_ids else 'same_chunk_context'}
                for key,record in self.claims.items()
                if key in claim_ids or record.get('source',{}).get('chunk_id') in chunks]
