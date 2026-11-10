import { FormEvent, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

type Evidence = { evidence_id: string; chunk_id: string; document_id: string; source_path: string; file_type: string; text: string; location_type?: string; location_number?: number; score: number }
type Answer = { answer: string; grounded: boolean; mode: string; citation_validation?: { valid: boolean; citations: string[]; errors: string[] } }
type Retrieval = { mode: string; rrf_k?: number; lexical_candidates?: number; dense_candidates?: number; reason?: string }
type Result = { answer: Answer; evidence: Evidence[]; retrieval: Retrieval; status: string }
type Dashboard = { documents: number; source_files: number; chunks: number; retrieval: string; dense_index_ready: boolean; evidence?: { entities: number; claims: number; events: number; relationships: number } | null }
type DocumentRecord = { document_id: string; source_path: string; file_type: string; chunk_count: number }

const examples = ['What is an operating system?', 'Explain process scheduling', 'What is normalization in DBMS?']
const nav = [['overview', 'Overview'], ['ask', 'Ask Documents'], ['library', 'Document Library'], ['evidence', 'Evidence Explorer']] as const
type Panel = typeof nav[number][0]

function App() {
  const [panel, setPanel] = useState<Panel>('overview')
  const [query, setQuery] = useState(examples[0])
  const [result, setResult] = useState<Result | null>(null)
  const [stats, setStats] = useState<Dashboard | null>(null)
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeEvidence, setActiveEvidence] = useState<string | null>(null)
  const [documentFilter, setDocumentFilter] = useState('')

  useEffect(() => {
    Promise.all([fetch('/api/dashboard'), fetch('/api/documents/')])
      .then(async ([dashboard, library]) => {
        if (dashboard.ok) setStats(await dashboard.json())
        if (library.ok) setDocuments((await library.json()).items)
      })
      .catch(() => setError('TraceRAG API is unavailable. Start the backend and refresh this page.'))
  }, [])

  const evidenceTotal = stats?.evidence ? stats.evidence.entities + stats.evidence.claims + stats.evidence.events + stats.evidence.relationships : null
  const filteredDocuments = useMemo(() => documents.filter(item => item.document_id.toLowerCase().includes(documentFilter.toLowerCase())), [documents, documentFilter])

  async function investigate(event?: FormEvent, value = query) {
    event?.preventDefault()
    if (value.trim().length < 2) return
    setLoading(true); setError(''); setActiveEvidence(null); setPanel('ask')
    try {
      const response = await fetch('/api/investigations/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: value, top_k: 6 }) })
      if (!response.ok) throw new Error('The investigation service returned an error.')
      setResult(await response.json())
    } catch (err) { setError(err instanceof Error ? err.message : 'Something went wrong.') }
    finally { setLoading(false) }
  }

  return <main className="app-shell">
    <header className="topbar">
      <button className="brand" onClick={() => setPanel('overview')}><span className="brand-mark">TR</span> TraceRAG</button>
      <nav aria-label="Main navigation">{nav.map(([id, label]) => <button key={id} className={panel === id ? 'nav-link active' : 'nav-link'} onClick={() => setPanel(id)}>{label}</button>)}</nav>
      <span className={stats?.dense_index_ready ? 'system-state ready' : 'system-state'}>{stats?.dense_index_ready ? 'Hybrid index ready' : 'BM25 mode'}</span>
    </header>
    {error && <div className="notice error">{error}</div>}
    {panel === 'overview' && <Overview stats={stats} evidenceTotal={evidenceTotal} onAsk={() => setPanel('ask')} />}
    {panel === 'ask' && <AskDocuments query={query} setQuery={setQuery} result={result} loading={loading} onSubmit={investigate} activeEvidence={activeEvidence} setActiveEvidence={setActiveEvidence} />}
    {panel === 'library' && <DocumentLibrary documents={filteredDocuments} filter={documentFilter} setFilter={setDocumentFilter} />}
    {panel === 'evidence' && <EvidenceExplorer result={result} activeEvidence={activeEvidence} setActiveEvidence={setActiveEvidence} onAsk={() => setPanel('ask')} />}
    <footer>TraceRAG keeps every result connected to its original evidence.</footer>
  </main>
}

function Overview({ stats, evidenceTotal, onAsk }: { stats: Dashboard | null; evidenceTotal: number | null; onAsk: () => void }) {
  return <section className="page overview-page">
    <div className="hero-copy"><div className="eyebrow">EVIDENCE-CENTRIC HYBRID RAG</div><h1>Ask with confidence.<br /><em>Trace every answer.</em></h1><p>TraceRAG retrieves document evidence, validates citations, and makes uncertainty visible.</p><button className="primary" onClick={onAsk}>Ask your documents -&gt;</button></div>
    <section className="metric-grid" aria-label="Live corpus status"><Metric value={stats?.documents ?? '--'} label="logical documents" /><Metric value={stats?.source_files ?? '--'} label="source files" /><Metric value={stats?.chunks?.toLocaleString() ?? '--'} label="indexed chunks" /><Metric value={evidenceTotal?.toLocaleString() ?? '--'} label="evidence records" accent /></section>
    <section className="status-grid"><Status label="Retrieval" value={stats?.retrieval ?? 'Checking API'} ok={Boolean(stats)} /><Status label="Dense index" value={stats?.dense_index_ready ? 'Available' : 'Not built'} ok={Boolean(stats?.dense_index_ready)} /><Status label="Answer policy" value="Citations required" ok /><Status label="Evidence validation" value={stats?.evidence ? 'Completed' : 'Not available'} ok={Boolean(stats?.evidence)} /></section>
  </section>
}

function AskDocuments({ query, setQuery, result, loading, onSubmit, activeEvidence, setActiveEvidence }: { query: string; setQuery: (value: string) => void; result: Result | null; loading: boolean; onSubmit: (event?: FormEvent, value?: string) => Promise<void>; activeEvidence: string | null; setActiveEvidence: (value: string | null) => void }) {
  return <section className="page ask-page"><div className="page-heading"><div className="eyebrow">ASK DOCUMENTS</div><h2>Evidence before answers.</h2><p>Ask a question in plain language. TraceRAG retrieves original passages before it responds.</p></div><form className="search" onSubmit={onSubmit}><span className="search-icon">Q</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Ask a question about your documents" aria-label="Investigation query" /><button disabled={loading}>{loading ? 'Investigating...' : 'Investigate'}</button></form><div className="suggestions">Try: {examples.map((item, index) => <button key={item} onClick={() => { setQuery(item); void onSubmit(undefined, item) }}>{index ? ' | ' : ''}{item}</button>)}</div>{loading && <LoadingState />}{result && !loading && <Investigation result={result} activeEvidence={activeEvidence} setActiveEvidence={setActiveEvidence} />}{!result && !loading && <Empty title="Start an evidence investigation" description="Answers remain linked to exact source passages, documents, and page or slide locations." />}</section>
}

function Investigation({ result, activeEvidence, setActiveEvidence }: { result: Result; activeEvidence: string | null; setActiveEvidence: (value: string | null) => void }) {
  const generated = result.answer.mode === 'ollama_grounded'
  return <section className="investigation"><div className="result-heading"><div><div className="eyebrow">INVESTIGATION RESULT</div><h3>{generated ? 'Cited student answer' : 'Evidence-first result'}</h3></div><span className={generated ? 'system-state ready' : 'system-state'}>{generated ? 'Grounded local RAG' : 'Evidence-only fallback'}</span></div><article className="answer-card"><span className="answer-kicker">{generated ? 'TRACE RAG ANSWER' : 'SYSTEM STATUS'}</span><p>{result.answer.answer}</p><small>{generated ? 'Every cited identifier is checked against retrieved evidence.' : 'The local model was unavailable or failed citation validation, so TraceRAG did not fabricate an answer.'}</small></article><div className="retrieval-strip"><span>Mode: <b>{result.retrieval.mode}</b></span><span>Lexical candidates: <b>{result.retrieval.lexical_candidates ?? 0}</b></span><span>Dense candidates: <b>{result.retrieval.dense_candidates ?? 0}</b></span></div><EvidenceGrid items={result.evidence} activeEvidence={activeEvidence} setActiveEvidence={setActiveEvidence} /></section>
}

function DocumentLibrary({ documents, filter, setFilter }: { documents: DocumentRecord[]; filter: string; setFilter: (value: string) => void }) {
  return <section className="page"><div className="page-heading"><div className="eyebrow">DOCUMENT LIBRARY</div><h2>Indexed source material.</h2><p>These are the documents currently available to TraceRAG retrieval.</p></div><input className="library-search" value={filter} onChange={event => setFilter(event.target.value)} placeholder="Filter documents" aria-label="Filter documents" /><div className="document-list">{documents.map(document => <article key={document.document_id} className="document-row"><div><h3>{document.document_id}</h3><span>{document.source_path}</span></div><div className="document-meta"><b>{document.chunk_count.toLocaleString()}</b> chunks<br /><span>{document.file_type.toUpperCase()}</span></div></article>)}{!documents.length && <Empty title="No matching documents" description="Try a different filter or verify that the backend is running." />}</div></section>
}

function EvidenceExplorer({ result, activeEvidence, setActiveEvidence, onAsk }: { result: Result | null; activeEvidence: string | null; setActiveEvidence: (value: string | null) => void; onAsk: () => void }) {
  return <section className="page"><div className="page-heading"><div className="eyebrow">EVIDENCE EXPLORER</div><h2>Inspect the source trail.</h2><p>Evidence shown here comes from the latest investigation, retaining document and location provenance.</p></div>{result ? <EvidenceGrid items={result.evidence} activeEvidence={activeEvidence} setActiveEvidence={setActiveEvidence} /> : <Empty title="No retrieved evidence yet" description="Run an investigation first, then inspect its source passages here." action="Ask documents" onAction={onAsk} />}</section>
}

function EvidenceGrid({ items, activeEvidence, setActiveEvidence }: { items: Evidence[]; activeEvidence: string | null; setActiveEvidence: (value: string | null) => void }) { return <><div className="evidence-header"><h3>Supporting evidence <span>{items.length}</span></h3><p>Original source text only</p></div><div className="evidence-grid">{items.map(item => <EvidenceCard key={item.evidence_id} item={item} expanded={activeEvidence === item.evidence_id} onToggle={() => setActiveEvidence(activeEvidence === item.evidence_id ? null : item.evidence_id)} />)}</div></> }
function EvidenceCard({ item, expanded, onToggle }: { item: Evidence; expanded: boolean; onToggle: () => void }) { const location = item.location_number ? `${item.location_type ?? 'section'} ${item.location_number}` : 'source excerpt'; return <article className={expanded ? 'evidence-card open' : 'evidence-card'}><div className="evidence-top"><span className="citation">[{item.evidence_id}]</span><span className="score">score {item.score}</span></div><h4>{item.document_id}</h4><div className="source-line"><span>{item.file_type.toUpperCase()}</span><b>|</b><span>{location}</span></div><p className={expanded ? '' : 'clamp'}>{item.text}</p><button onClick={onToggle}>{expanded ? 'Show less' : 'Read evidence'} -&gt;</button></article> }
function Metric({ value, label, accent = false }: { value: string | number; label: string; accent?: boolean }) { return <article className={accent ? 'metric accent' : 'metric'}><strong>{value}</strong><span>{label}</span></article> }
function Status({ label, value, ok = false }: { label: string; value: string; ok?: boolean }) { return <article className="status-card"><span>{label}</span><b className={ok ? 'ok' : ''}>{ok ? '* ' : 'o '}{value}</b></article> }
function Empty({ title, description, action, onAction }: { title: string; description: string; action?: string; onAction?: () => void }) { return <section className="empty-state"><div className="empty-orbit">TR</div><h3>{title}</h3><p>{description}</p>{action && onAction && <button className="primary" onClick={onAction}>{action}</button>}</section> }
function LoadingState() { return <section className="empty-state"><div className="pulse" /><h3>Reviewing the document record</h3><p>TraceRAG is retrieving and validating evidence.</p></section> }

createRoot(document.getElementById('root')!).render(<App />)
