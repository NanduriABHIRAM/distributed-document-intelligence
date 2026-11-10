export type Evidence = {
  evidence_id: string
  chunk_id: string
  document_id: string
  source_path: string
  file_type: string
  text: string
  location_type?: string | null
  location_number?: number | null
  score: number
}

export type Answer = {
  answer: string
  grounded: boolean
  mode: string
  citation_validation?: { valid: boolean; citations: string[]; errors: string[] }
}

export type Retrieval = {
  mode: string
  lexical_candidates?: number
  dense_candidates?: number
  graph_candidates?: number
  latency_ms?: number
  reranker?: string | null
}

export type Comparison = {
  label: string
  reason: string
  claim_ids: string[]
  evidence: string[]
  needs_review: boolean
  temporal?: { relationship: string }
}

export type InvestigationResult = {
  query: string
  answer: Answer
  evidence: Evidence[]
  retrieval: Retrieval
  status: string
  analysis?: { comparisons: Comparison[]; claims_available: number; truncated: boolean }
}

export type Dashboard = {
  documents: number
  source_files: number
  chunks: number
  retrieval: string
  dense_index_ready: boolean
  generation_model_available?: boolean
  evidence?: {
    entities: number
    claims: number
    events: number
    relationships: number
    invalid?: number
    needs_review?: number
    complete?: boolean
  } | null
}

export type DocumentRecord = {
  document_id: string
  source_path: string
  file_type: string
  chunk_count: number
}
