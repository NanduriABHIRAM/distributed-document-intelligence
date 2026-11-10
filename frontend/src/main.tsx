import { FormEvent, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

type Evidence = {
  evidence_id: string; chunk_id: string; document_id: string; source_path: string; file_type: string;
  text: string; location_type?: string; location_number?: number; score: number
}
type Result = { answer: { answer: string; grounded: boolean; mode: string }; evidence: Evidence[]; status: string }
type Dashboard = { documents: number; chunks: number; retrieval: string; evidence?: { entities: number; claims: number; events: number; relationships: number } | null }

const examples = ['What is an operating system?', 'Explain process scheduling', 'What is normalization in DBMS?']

function App() {
  const [query, setQuery] = useState(examples[0])
  const [result, setResult] = useState<Result | null>(null)
  const [stats, setStats] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeEvidence, setActiveEvidence] = useState<string | null>(null)

  useEffect(() => { fetch('/api/dashboard').then(r => r.ok ? r.json() : null).then(setStats).catch(() => null) }, [])

  async function investigate(event?: FormEvent, value = query) {
    event?.preventDefault()
    if (value.trim().length < 2) return
    setLoading(true); setError(''); setActiveEvidence(null)
    try {
      const response = await fetch('/api/investigations/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: value, top_k: 6 }) })
      if (!response.ok) throw new Error('The investigation service is not available.')
      setResult(await response.json())
    } catch (err) { setError(err instanceof Error ? err.message : 'Something went wrong.') }
    finally { setLoading(false) }
  }

  return <main className="shell">
    <nav className="topbar">
      <a className="brand" href="#top"><span className="brand-mark">✦</span> Evidence Atlas</a>
      <div className="nav-status"><i /> Evidence-first research workspace</div>
    </nav>

    <section className="hero" id="top">
      <div className="eyebrow">DISTRIBUTED DOCUMENT INTELLIGENCE</div>
      <h1>Investigate the record.<br/><em>Keep every source in view.</em></h1>
      <p>Search your corpus with traceable evidence, not black-box answers.</p>
      <form className="search" onSubmit={investigate}>
        <span className="search-icon">⌕</span>
        <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Ask a question about your documents" aria-label="Investigation query" />
        <button disabled={loading}>{loading ? 'Investigating…' : 'Investigate'} <span>→</span></button>
      </form>
      <div className="suggestions">Try: {examples.map((item, index) => <button key={item} onClick={() => { setQuery(item); investigate(undefined, item) }}>{index ? '· ' : ''}{item}</button>)}</div>
    </section>

    <section className="metrics" aria-label="Corpus status">
      <Metric value={stats?.documents ?? '—'} label="documents indexed" />
      <Metric value={stats?.chunks?.toLocaleString() ?? '—'} label="source chunks" />
      <Metric value={stats?.evidence ? stats.evidence.claims.toLocaleString() : 'Ready'} label={stats?.evidence ? 'evidence claims' : 'evidence pipeline'} />
      <Metric value="100%" label="provenance retained" accent />
    </section>

    {error && <div className="notice error">{error} Start the API with <code>uvicorn api.main:app --reload</code>.</div>}
    {!result && !loading && <section className="empty-state"><div className="empty-orbit"><span>✦</span></div><h2>Start an evidence investigation</h2><p>Results will include the exact supporting text, document, and page or slide reference.</p></section>}
    {loading && <section className="empty-state"><div className="pulse"/><h2>Reviewing the document record</h2><p>Ranking lexical evidence and preserving its source trail.</p></section>}
    {result && <section className="investigation">
      <div className="result-heading"><div><div className="eyebrow">INVESTIGATION RESULT</div><h2>Evidence, not assumptions.</h2></div><span className="grounded">● Grounded baseline</span></div>
      <article className="answer-card"><span className="answer-kicker">SYSTEM FINDING</span><p>{result.answer.answer}</p><small>This baseline intentionally presents retrieved evidence rather than unverified generated claims.</small></article>
      <div className="evidence-header"><h3>Supporting evidence <span>{result.evidence.length}</span></h3><p>Ranked using {stats?.retrieval ?? 'lexical retrieval'}</p></div>
      <div className="evidence-grid">{result.evidence.map(item => <EvidenceCard key={item.evidence_id} item={item} expanded={activeEvidence === item.evidence_id} onToggle={() => setActiveEvidence(activeEvidence === item.evidence_id ? null : item.evidence_id)} />)}</div>
    </section>}
    <footer>Evidence Atlas · Every result remains linked to its original document fragment.</footer>
  </main>
}

function Metric({ value, label, accent = false }: { value: string | number; label: string; accent?: boolean }) { return <div className={accent ? 'metric accent' : 'metric'}><strong>{value}</strong><span>{label}</span></div> }
function EvidenceCard({ item, expanded, onToggle }: { item: Evidence; expanded: boolean; onToggle: () => void }) {
  const location = item.location_number ? `${item.location_type ?? 'section'} ${item.location_number}` : 'source excerpt'
  return <article className={expanded ? 'evidence-card open' : 'evidence-card'}><div className="evidence-top"><span className="citation">[{item.evidence_id}]</span><span className="score">relevance {item.score}</span></div><h4>{item.document_id}</h4><div className="source-line"><span>{item.file_type.toUpperCase()}</span><b>·</b><span>{location}</span></div><p className={expanded ? '' : 'clamp'}>{item.text}</p><button onClick={onToggle}>{expanded ? 'Show less' : 'Read evidence'} <span>↗</span></button></article>
}

createRoot(document.getElementById('root')!).render(<App />)
