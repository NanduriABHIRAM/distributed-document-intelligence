import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { errorMessage, request } from './api'
import { applyTheme, documentName, locationLabel, navigation, panelFromHash, retrievalLabel } from './ui'
import type { Panel } from './ui'
import type { Dashboard, DocumentRecord, Evidence, InvestigationResult, GraphData, GraphEdge, GraphNode } from './types'
import { OcrWorkspace } from './OcrWorkspace'
import { layoutGraph } from './graphLayout'
import { StudyChat } from './StudyChat'

const examples = ['What are the main findings?', 'Which statements disagree?', 'What changed over time?']

function Arrow() {
  return <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M5 15 15 5M5 5h10v10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
}

function ThemeIcon({ dark }: { dark: boolean }) {
  return <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
    {dark
      ? <><circle cx="10" cy="10" r="3" stroke="currentColor" strokeWidth="1.3" /><path d="M10 2v1.5M10 16.5V18M2 10h1.5M16.5 10H18M4.3 4.3l1.1 1.1m9.2 9.2 1.1 1.1M4.3 15.7l1.1-1.1m9.2-9.2 1.1-1.1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></>
      : <path d="M16.3 11.8A6.6 6.6 0 0 1 8.2 3.7a6.6 6.6 0 1 0 8.1 8.1Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />}
  </svg>
}

function useWorkspace() {
  const [stats, setStats] = useState<Dashboard | null>(null)
  const [documents, setDocuments] = useState<DocumentRecord[] | null>(null)
  const [statsError, setStatsError] = useState('')
  const [documentsError, setDocumentsError] = useState('')
  const [loading, setLoading] = useState(true)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setStatsError('')
    setDocumentsError('')
    const loadStats = request<Dashboard>('/dashboard', { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) setStats(value) })
      .catch(error => { if (!controller.signal.aborted) setStatsError(errorMessage(error)) })
    const loadDocuments = request<{ items: DocumentRecord[] }>('/documents/', { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) setDocuments(value.items) })
      .catch(error => { if (!controller.signal.aborted) setDocumentsError(errorMessage(error)) })
    Promise.allSettled([loadStats, loadDocuments]).then(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [version])

  return { stats, documents, statsError, documentsError, loading, refresh: () => setVersion(value => value + 1) }
}

export default function App() {
  const workspace = useWorkspace()
  const { stats, documents, loading: workspaceLoading, statsError } = workspace
  const [panel, setPanel] = useState<Panel>(() => panelFromHash(window.location.hash))
  const [theme, setTheme] = useState<'light' | 'dark'>(() => document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [result, setResult] = useState<InvestigationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [queryError, setQueryError] = useState('')
  const [cancelled, setCancelled] = useState(false)
  const [activeEvidence, setActiveEvidence] = useState<string | null>(null)
  const [documentFilter, setDocumentFilter] = useState('')
  const activeRequest = useRef<AbortController | null>(null)
  const mainRef = useRef<HTMLElement>(null)
  const previousPanel = useRef(panel)
  const hasNoDocuments = documents !== null && documents.length === 0 && !workspace.documentsError

  useEffect(() => {
    const onHash = () => setPanel(panelFromHash(window.location.hash))
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    document.title = `${navigation.find(([id]) => id === panel)?.[1]} · TraceRAG`
    if (previousPanel.current !== panel) mainRef.current?.focus({ preventScroll: true })
    previousPanel.current = panel
  }, [panel])

  useEffect(() => {
    applyTheme(theme)
    try { localStorage.setItem('tracerag-theme', theme) } catch { /* Storage may be unavailable. */ }
  }, [theme])

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === 'tracerag-theme') setTheme(event.newValue === 'dark' ? 'dark' : 'light')
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  useEffect(() => () => activeRequest.current?.abort(), [])

  function navigate(next: Panel) {
    window.location.hash = next
    setPanel(next)
  }

  async function investigate(value = query) {
    const question = value.trim()
    if (question.length < 2 || question.length > 500) {
      setQueryError('Enter a question between 2 and 500 characters.')
      return
    }
    if (hasNoDocuments) return
    activeRequest.current?.abort()
    const controller = new AbortController()
    activeRequest.current = controller
    setLoading(true)
    setQueryError('')
    setCancelled(false)
    setQuery(question)
    setSubmittedQuery(question)
    setResult(null)
    setActiveEvidence(null)
    navigate('ask')
    try {
      const value = await request<InvestigationResult>('/investigations/query', {
        method: 'POST', signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: question, top_k: 6 }),
      }, 150_000)
      if (activeRequest.current === controller && !controller.signal.aborted) {
        setResult({ ...value, query: value.query || question })
      }
    } catch (error) {
      if (activeRequest.current === controller && !controller.signal.aborted) setQueryError(errorMessage(error))
    } finally {
      if (activeRequest.current === controller) {
        activeRequest.current = null
        setLoading(false)
      }
    }
  }

  function cancelSearch() {
    activeRequest.current?.abort()
    activeRequest.current = null
    setLoading(false)
    setCancelled(true)
  }

  function openCitation(id: string) {
    setActiveEvidence(id)
    requestAnimationFrame(() => {
      const element = document.getElementById(`source-${id}`)
      element?.focus({ preventScroll: true })
      element?.scrollIntoView({ behavior: 'auto', block: 'nearest' })
    })
  }

  const connection = statsError ? 'Status unavailable'
    : !stats ? (workspaceLoading ? 'Connecting' : 'Status unavailable')
    : stats.chunks === 0 ? 'No documents indexed'
    : stats.dense_index_ready ? 'Hybrid index ready' : 'Keyword search ready'

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="topbar">
      <a className="brand" href="#overview"><span className="brand-mark" aria-hidden="true">TR</span>TraceRAG</a>
      <nav aria-label="Main navigation">
        {navigation.map(([id, label]) => <a key={id} className={`nav-link${panel === id ? ' active' : ''}`} href={`#${id}`} aria-current={panel === id ? 'page' : undefined}>{label}</a>)}
      </nav>
      <div className="header-tools">
        <span className={`system-state${stats && stats.chunks > 0 && !statsError ? ' ready' : ''}`}>{connection}</span>
        <button className="theme-toggle" type="button" aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'} aria-pressed={theme === 'dark'} onClick={() => setTheme(value => value === 'light' ? 'dark' : 'light')}>
          <ThemeIcon dark={theme === 'dark'} /><span>{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>
        </button>
      </div>
    </header>

    <main id="main-content" ref={mainRef} tabIndex={-1}>
      {panel === 'overview' && <Overview workspace={workspace} onAsk={() => navigate('ask')} />}
      {panel === 'ocr' && <OcrWorkspace />}
      <div hidden={panel !== 'rag'}><StudyChat /></div>
      {panel === 'ask' && <section className="page ask-page">
        <PageHeading eyebrow="Ask documents" title="Evidence before answers.">Ask a question in plain language. TraceRAG retrieves original passages before it responds.</PageHeading>
        <form className="search" onSubmit={(event: FormEvent) => { event.preventDefault(); void investigate() }}>
          <span className="search-symbol" aria-hidden="true" />
          <input aria-label="Investigation query" aria-describedby={hasNoDocuments ? 'no-corpus-note' : undefined} aria-invalid={queryError ? true : undefined} value={query} onChange={event => { setQuery(event.target.value); setQueryError('') }} placeholder="Ask a question about your documents" minLength={2} maxLength={500} required disabled={hasNoDocuments} />
          <button type="submit" disabled={loading || hasNoDocuments || query.trim().length < 2}>Investigate <Arrow /></button>
        </form>
        {hasNoDocuments
          ? <p className="field-note" id="no-corpus-note">There are no indexed documents yet. <a href="#library">View your document library</a>.</p>
          : <div className="suggestions"><span>Try:</span>{examples.map(value => <button key={value} type="button" disabled={loading} onClick={() => void investigate(value)}>{value}</button>)}</div>}
        {queryError && <Notice message={queryError} action={submittedQuery ? 'Retry question' : undefined} onAction={() => void investigate(submittedQuery)} />}
        {loading && <div className="loading-state" role="status"><span className="pulse" aria-hidden="true" /><div><h2>Reviewing your documents</h2><p>Finding sources for “{submittedQuery}”</p></div><button type="button" className="text-button" onClick={cancelSearch}>Cancel</button></div>}
        {!loading && result && <Investigation result={result} activeEvidence={activeEvidence} setActiveEvidence={setActiveEvidence} onCitation={openCitation} />}
        {!loading && !result && !queryError && <Empty title={hasNoDocuments ? 'Your sources will appear here' : cancelled ? 'Investigation cancelled' : 'Start an evidence investigation'} description={hasNoDocuments ? 'Index your documents, then refresh the workspace to start asking questions.' : cancelled ? 'Your question is still above. You can edit it or try again.' : 'Answers stay connected to their source passages, with page and slide references.'} action={hasNoDocuments ? 'Refresh workspace' : undefined} onAction={workspace.refresh} />}
      </section>}
      {panel === 'library' && <DocumentLibrary workspace={workspace} filter={documentFilter} setFilter={setDocumentFilter} />}
      {panel === 'evidence' && <section className="page">
        <PageHeading eyebrow="Evidence explorer" title="Inspect the source trail.">Review the passages from your latest investigation, with their original document references.</PageHeading>
        {result?.evidence.length
          ? <><p className="query-context">For: <span>{result.query}</span></p><EvidenceGrid items={result.evidence} activeEvidence={activeEvidence} setActiveEvidence={setActiveEvidence} /></>
          : <Empty title="No retrieved evidence yet" description="Run an investigation to inspect its supporting source passages." action="Ask documents" onAction={() => navigate('ask')} />}
      </section>}
      {panel === 'graph' && <EvidenceGraph documents={documents || []} />}
    </main>
    <footer><span>TraceRAG keeps every result connected to its original evidence.</span><span>Document intelligence</span></footer>
    <div className="sr-only" role="status">{!loading && result ? `${result.evidence.length} supporting passages retrieved.` : ''}</div>
  </div>
}

type Workspace = ReturnType<typeof useWorkspace>

function Overview({ workspace, onAsk }: { workspace: Workspace; onAsk: () => void }) {
  const { stats, documents, statsError, documentsError, loading, refresh } = workspace
  const evidence = stats?.evidence
  const total = evidence ? evidence.entities + evidence.claims + evidence.events + evidence.relationships : null
  const reviewCount = (evidence?.invalid || 0) + (evidence?.needs_review || 0)
  const extraction = !stats ? 'Unavailable' : !evidence ? 'Not run' : reviewCount ? `${reviewCount.toLocaleString()} to review` : evidence.complete ? 'Processed' : 'Partial run'
  const value = (number: number | null | undefined) => number == null ? '—' : number.toLocaleString()

  return <section className="page overview-page" aria-busy={loading}>
    <div className="hero-copy">
      <div className="eyebrow">Evidence-centric hybrid RAG</div>
      <h1>Ask with confidence.<br /><em>Trace every answer.</em></h1>
      <p>TraceRAG retrieves document evidence, checks citations, and makes uncertainty visible.</p>
      <button className="primary" type="button" onClick={onAsk}>Ask your documents <Arrow /></button>
    </div>
    {statsError && <Notice message={statsError} action="Retry connection" onAction={refresh} disabled={loading} />}
    {documentsError && !statsError && <Notice message="The document library could not be refreshed. Some workspace counts are unavailable." action="Retry" onAction={refresh} disabled={loading} />}
    <section className="metric-grid" aria-label="Corpus totals">
      <Metric value={value(stats?.documents)} label="documents" />
      <Metric value={value(stats?.chunks)} label="indexed passages" />
      <Metric value={documents && !documentsError ? value(new Set(documents.map(item => item.file_type.toLowerCase())).size) : '—'} label="source formats" />
      <Metric value={value(total)} label="evidence records" accent />
    </section>
    <div className="workspace-footnote"><span>{stats?.graph ? `${stats.graph.nodes.toLocaleString()} graph entities · ${stats.graph.edges.toLocaleString()} validated relationships` : 'Graph statistics are unavailable.'}</span><a href="#graph">Open evidence graph</a></div>
    <section className="status-grid" aria-label="Workspace readiness">
      <Status label="Retrieval" value={!stats ? 'Unavailable' : stats.chunks === 0 ? 'Awaiting documents' : stats.dense_index_ready ? 'Hybrid search' : 'Keyword search'} ok={Boolean(stats?.chunks) && !statsError} />
      <Status label="Answer model" value={!stats ? 'Unavailable' : stats.generation_model_available ? 'Available' : 'Offline · excerpts available'} ok={stats?.generation_model_available === true && !statsError} />
      <Status label="Citation policy" value="Source support required" />
      <Status label="Evidence extraction" value={extraction} ok={Boolean(evidence?.complete && !reviewCount && !statsError)} />
    </section>
    <div className="workspace-footnote"><span>{loading ? 'Refreshing workspace…' : statsError ? 'Showing the last available counts.' : stats?.documents === 0 ? 'Your workspace is ready for documents.' : 'Counts reflect the current local corpus.'}</span><button type="button" className="text-button" onClick={refresh} disabled={loading}>Refresh</button></div>
  </section>
}

function PageHeading({ eyebrow, title, children }: { eyebrow: string; title: string; children: ReactNode }) {
  return <div className="page-heading"><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{children}</p></div>
}

function DocumentLibrary({ workspace, filter, setFilter }: { workspace: Workspace; filter: string; setFilter: (value: string) => void }) {
  const { documents, documentsError, loading, refresh } = workspace
  const filtered = useMemo(() => (documents || []).filter(item => `${documentName(item.source_path, item.document_id)} ${item.source_path} ${item.file_type}`.toLocaleLowerCase().includes(filter.trim().toLocaleLowerCase())).sort((a, b) => documentName(a.source_path, a.document_id).localeCompare(documentName(b.source_path, b.document_id))), [documents, filter])

  return <section className="page" aria-busy={loading && documents === null}>
    <PageHeading eyebrow="Document library" title="Indexed source material.">The documents currently available for retrieval in this workspace.</PageHeading>
    {documentsError && <Notice message={documentsError} action="Retry" onAction={refresh} disabled={loading} />}
    {documents?.length ? <>
      <div className="library-toolbar"><input type="search" className="library-search" value={filter} onChange={event => setFilter(event.target.value)} placeholder="Filter by name, path or format" aria-label="Filter documents" /><span className="result-count" role="status">{filtered.length.toLocaleString()} of {documents.length.toLocaleString()} documents</span><button type="button" className="text-button" onClick={refresh} disabled={loading}>Refresh</button></div>
      <div className="document-list">{filtered.map(item => <article key={item.document_id} className="document-row"><div><h2>{documentName(item.source_path, item.document_id)}</h2><span>{item.source_path}</span></div><div className="document-meta"><b>{item.chunk_count.toLocaleString()}</b> passages<span>{item.file_type.toUpperCase()}</span></div></article>)}</div>
      {!filtered.length && <Empty title="No matching documents" description="Try a different filename or clear the filter." action="Clear filter" onAction={() => setFilter('')} />}
    </> : loading ? <div className="loading-state" role="status"><span className="pulse" aria-hidden="true" /><p>Loading your document library…</p></div>
      : !documentsError && <Empty title="No documents indexed yet" description="Your processed documents will appear here after ingestion." action="Refresh library" onAction={refresh} />}
  </section>
}

function CitedText({ text, evidence, onCitation }: { text: string; evidence: Evidence[]; onCitation: (id: string) => void }) {
  const allowed = new Set(evidence.map(item => item.evidence_id))
  return <>{text.split(/(\[E\d+\])/g).map((part, index) => {
    const id = part.slice(1, -1)
    return /^\[E\d+\]$/.test(part) && allowed.has(id)
      ? <button key={index} className="reference" type="button" aria-label={`Read source ${id}`} onClick={() => onCitation(id)}>{part}</button>
      : part
  })}</>
}

function Investigation({ result, activeEvidence, setActiveEvidence, onCitation }: { result: InvestigationResult; activeEvidence: string | null; setActiveEvidence: (value: string | null) => void; onCitation: (id: string) => void }) {
  if (!result.evidence.length) return <div className="investigation"><p className="query-context">For: <span>{result.query}</span></p><Empty title="No supporting evidence found" description="Try a more specific question or check whether the relevant document is in your library." /></div>
  const cited = (result.answer.mode === 'ollama_grounded' || result.answer.mode === 'ollama_citation_valid_unverified') && result.answer.citation_validation?.valid
  const exact = result.answer.answer_status === 'VERIFIED_EXACT'
  return <section className="investigation" aria-label="Investigation result">
    <div className="result-heading"><div><div className="eyebrow">Investigation result</div><h2>{cited ? 'Cited answer' : 'Source passages'}</h2></div><span className="system-state">{cited ? exact ? 'Exact source match' : 'Citations linked · paraphrase unverified' : 'Excerpts available'}</span></div>
    <p className="query-context">For: <span>{result.query}</span></p>
    <article className="answer-card"><span className="answer-kicker">{cited ? 'TraceRAG answer' : 'Evidence summary'}</span><p><CitedText text={result.answer.answer} evidence={result.evidence} onCitation={onCitation} /></p>{cited && <small>Select a reference to read its supporting passage.</small>}</article>
    <details className="retrieval-details"><summary>Search details <span>{retrievalLabel(result.retrieval.mode)}</span></summary><dl><div><dt>Keyword candidates</dt><dd>{result.retrieval.lexical_candidates ?? '—'}</dd></div><div><dt>Semantic candidates</dt><dd>{result.retrieval.dense_candidates ?? '—'}</dd></div><div><dt>Graph candidates</dt><dd>{result.retrieval.graph_candidates ?? '—'}</dd></div>{result.retrieval.latency_ms != null && <div><dt>Retrieval time</dt><dd>{(result.retrieval.latency_ms / 1000).toFixed(2)} s</dd></div>}</dl></details>
    <Reasoning result={result} />
    <EvidenceGrid items={result.evidence} activeEvidence={activeEvidence} setActiveEvidence={setActiveEvidence} />
  </section>
}

const graphColour = (type: string) => ({ PERSON: '#6c83a2', ORGANIZATION: '#795e40', LOCATION: '#507766', DATE: '#8b687d', EVENT: '#a17036' }[type] || '#666b62')

function EvidenceGraph({ documents }: { documents: DocumentRecord[] }) {
  const [data, setData] = useState<GraphData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [type, setType] = useState('')
  const [documentId, setDocumentId] = useState('')
  const [selected, setSelected] = useState<GraphNode | GraphEdge | null>(null)
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const drag = useRef<{ x: number; y: number } | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(''); setSelected(null)
    const query = new URLSearchParams()
    if (type) query.set('entity_type', type)
    if (documentId) query.set('document_id', documentId)
    if (search.trim()) query.set('search', search.trim())
    request<GraphData>(`/graph${query.size ? `?${query}` : ''}`, { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) setData(value) })
      .catch(value => { if (!controller.signal.aborted) setError(errorMessage(value)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [type, documentId, search])

  const types = useMemo(() => Array.from(new Set(['PERSON', 'ORGANIZATION', 'LOCATION', 'DATE', 'EVENT', ...(data?.nodes || []).map(node => node.entity_type)])).sort(), [data])
  const nodes = data?.nodes || []
  const nodeIds = new Set(nodes.map(node => node.id))
  const edges = (data?.edges || []).filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))
  const layout = useMemo(() => layoutGraph(data?.nodes || [], data?.edges || []), [data])
  const positions = layout.positions
  const selectedNode = selected && 'entity_type' in selected ? selected as GraphNode : null
  const selectedEdge = selected && 'relationship_type' in selected ? selected as GraphEdge : null
  const connected = new Set(selectedNode ? [selectedNode.id, ...edges.filter(edge => edge.source === selectedNode.id || edge.target === selectedNode.id).flatMap(edge => [edge.source, edge.target])] : [])

  return <section className="page graph-page">
    <PageHeading eyebrow="Evidence graph" title="Relationships backed by source evidence.">Browse only validated entity relationships extracted from the current evidence records.</PageHeading>
    <div className="graph-toolbar"><input className="library-search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search entities" aria-label="Search graph entities" />
      <select value={type} onChange={event => setType(event.target.value)} aria-label="Filter by entity type"><option value="">All entity types</option>{types.map(value => <option key={value}>{value}</option>)}</select>
      <select value={documentId} onChange={event => setDocumentId(event.target.value)} aria-label="Filter by document"><option value="">All documents</option>{documents.map(document => <option key={document.document_id} value={document.document_id}>{documentName(document.source_path, document.document_id)}</option>)}</select>
      <div className="graph-zoom"><button type="button" aria-label="Zoom in" onClick={() => setZoom(value => Math.min(2.4, value + .2))}>+</button><button type="button" aria-label="Zoom out" onClick={() => setZoom(value => Math.max(.5, value - .2))}>−</button><button type="button" onClick={() => { setZoom(1); setOffset({ x: 0, y: 0 }) }}>Reset</button></div>
    </div>
    {loading ? <div className="loading-state" role="status"><span className="pulse" /><p>Loading evidence graph…</p></div>
      : error ? <Notice message={error} />
      : !nodes.length ? <Empty title="No evidence relationships available" description="No validated entity relationships were found in the current evidence output. Run evidence extraction, then rebuild the graph." />
      : <>{data?.truncated && <p className="field-note">Showing the first 800 matching entities, prioritising relationship endpoints. Search or filter to narrow the graph.</p>}<div className="graph-legend"><span>{nodes.length} entities ? {edges.length} relationships</span>{types.map(value => <span key={value}><i style={{ background: graphColour(value) }} />{value.toLowerCase()}</span>)}<span>Select an entity to highlight its connections. Drag to pan; scroll to explore.</span></div><div className="graph-layout"><div className="graph-canvas" onPointerDown={event => { if ((event.target as Element).closest('.graph-node, .graph-edge')) return; drag.current = { x: event.clientX - offset.x, y: event.clientY - offset.y }; event.currentTarget.setPointerCapture(event.pointerId) }} onPointerMove={event => { if (drag.current) setOffset({ x: event.clientX - drag.current.x, y: event.clientY - drag.current.y }) }} onPointerUp={() => { drag.current = null }} onPointerCancel={() => { drag.current = null }}>
        <svg style={{ width: layout.width * zoom, height: layout.height * zoom }} viewBox={`0 0 ${layout.width} ${layout.height}`} role="group" aria-label={`${nodes.length} entities and ${edges.length} relationships`}><g transform={`translate(${offset.x / zoom} ${offset.y / zoom})`}>
          {edges.map(edge => { const a = positions[edge.source]; const b = positions[edge.target]; if (!a || !b) return null; return <g key={edge.id} className={`graph-edge${selectedNode && edge.source !== selectedNode.id && edge.target !== selectedNode.id ? ' dimmed' : ''}`} role="button" tabIndex={0} aria-label={`${edge.label}: ${nodes.find(node => node.id === edge.source)?.label} to ${nodes.find(node => node.id === edge.target)?.label}`} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelected(edge) } }} onClick={() => setSelected(edge)}><line x1={a.x} y1={a.y} x2={b.x} y2={b.y} />{(selectedEdge?.id === edge.id || selectedNode?.id === edge.source || selectedNode?.id === edge.target) && <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 8}>{edge.label}</text>}<title>{edge.label}</title></g> })}
          {nodes.map(node => { const point = positions[node.id]; return <g key={node.id} className={`graph-node${selectedNode?.id === node.id ? ' active' : ''}${selectedNode && !connected.has(node.id) ? ' dimmed' : ''}`} transform={`translate(${point.x} ${point.y})`} role="button" tabIndex={0} aria-label={`${node.label}, ${node.entity_type}`} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelected(node) } }} onClick={() => setSelected(node)}><title>{node.label}</title><circle r="18" fill={graphColour(node.entity_type)} /><text y="35">{node.label.length > 20 ? `${node.label.slice(0, 19)}…` : node.label}</text></g> })}
        </g></svg></div>
        <aside className="graph-details">{selected && <button className="text-button" onClick={() => setSelected(null)}>Clear selection</button>}<h2>{selectedNode ? selectedNode.label : selectedEdge ? selectedEdge.label : 'Select a node or relationship'}</h2>{selectedNode && <><p><b>{selectedNode.entity_type}</b></p><h3>Connected relationships</h3><div className="connection-list">{edges.filter(edge => edge.source === selectedNode.id || edge.target === selectedNode.id).map(edge => <button key={edge.id} className="text-button" onClick={() => setSelected(edge)}>{nodes.find(node => node.id === edge.source)?.label} &rarr; {edge.label} &rarr; {nodes.find(node => node.id === edge.target)?.label}</button>)}</div><dl><div><dt>Document</dt><dd>{selectedNode.document_id || '—'}</dd></div><div><dt>Chunk</dt><dd>{selectedNode.chunk_id || '—'}</dd></div><div><dt>Source</dt><dd>{String(selectedNode.source.source_path || '—')}</dd></div></dl><a href="#library">Open document library</a></>}{selectedEdge && <><p>{selectedEdge.relationship_type}</p><dl><div><dt>Supporting chunk</dt><dd>{String(selectedEdge.provenance.chunk_id || '—')}</dd></div><div><dt>Location</dt><dd>{String(selectedEdge.provenance.location_type || 'source')} {String(selectedEdge.provenance.location_number || '')}</dd></div><div><dt>Source</dt><dd>{String(selectedEdge.provenance.source_path || '—')}</dd></div></dl></>}</aside>
      </div></>}
  </section>
}

function Reasoning({ result }: { result: InvestigationResult }) {
  const analysis = result.analysis
  if (!analysis?.claims_available) return null
  const conflicts = analysis.comparisons.filter(item => item.label === 'contradiction').length
  return <details className={`reasoning${conflicts ? ' has-conflicts' : ''}`} open={conflicts > 0 ? true : undefined}><summary>Claim comparisons <span>{conflicts ? `${conflicts} potential ${conflicts === 1 ? 'conflict' : 'conflicts'}` : `${analysis.comparisons.length} ${analysis.comparisons.length === 1 ? 'comparison' : 'comparisons'}`}</span></summary>
    {!analysis.comparisons.length && <p>No conclusive comparison was established. This does not establish that the documents agree.</p>}
    {analysis.comparisons.map((item, index) => <article className="comparison" key={`${item.claim_ids.join('-')}-${index}`}><h3>{item.label.replaceAll('_', ' ')}{item.needs_review && <span>Needs review</span>}</h3><p>{item.reason}</p>{item.evidence.map((text, i) => <blockquote key={i}>{text}</blockquote>)}{item.temporal && <small>Time relationship: {item.temporal.relationship.replaceAll('_', ' ')}</small>}</article>)}
    {analysis.truncated && <p className="field-note">The comparison limit was reached. Additional claims remain unexamined.</p>}
  </details>
}

function EvidenceGrid({ items, activeEvidence, setActiveEvidence }: { items: Evidence[]; activeEvidence: string | null; setActiveEvidence: (value: string | null) => void }) {
  return <><div className="evidence-header"><h2>Supporting evidence <span>/ {items.length}</span></h2><p>Original source passages</p></div><div className="evidence-grid">{items.map(item => <EvidenceCard key={item.evidence_id} item={item} expanded={activeEvidence === item.evidence_id} onToggle={() => setActiveEvidence(activeEvidence === item.evidence_id ? null : item.evidence_id)} />)}</div></>
}

function EvidenceCard({ item, expanded, onToggle }: { item: Evidence; expanded: boolean; onToggle: () => void }) {
  const id = `source-${item.evidence_id}`
  return <article className={`evidence-card${expanded ? ' open' : ''}`} id={id} tabIndex={-1} aria-label={`Source ${item.evidence_id}: ${documentName(item.source_path, item.document_id)}`}>
    <div className="evidence-top"><span className="citation">[{item.evidence_id}]</span><span>{item.file_type.toUpperCase()}</span></div>
    <h3>{documentName(item.source_path, item.document_id)}</h3>
    <div className="source-line">{locationLabel(item)}</div>
    <p className={`source-text${expanded ? '' : ' clamp'}`}>{item.text}</p>
    <div id={`${id}-details`} hidden={!expanded} className="source-details"><dl><div><dt>Source</dt><dd>{item.source_path}</dd></div><div><dt>Chunk</dt><dd>{item.chunk_id}</dd></div>{Number.isFinite(item.score) && <div><dt>Retrieval score</dt><dd>{item.score.toPrecision(4)}</dd></div>}</dl></div>
    <button type="button" className="text-button" aria-expanded={expanded} aria-controls={`${id}-details`} onClick={onToggle}>{expanded ? 'Show less' : 'Read evidence'} <Arrow /></button>
  </article>
}

function Metric({ value, label, accent = false }: { value: string; label: string; accent?: boolean }) {
  return <article className={`metric${accent ? ' accent' : ''}`}><strong>{value}</strong><span>{label}</span></article>
}

function Status({ label, value, ok = false }: { label: string; value: string; ok?: boolean }) {
  return <article className="status-card"><span>{label}</span><b className={ok ? 'ok' : undefined}>{value}</b></article>
}

function Notice({ message, action, onAction, disabled }: { message: string; action?: string; onAction?: () => void; disabled?: boolean }) {
  return <div className="notice" role="alert"><p>{message}</p>{action && onAction && <button className="text-button" type="button" onClick={onAction} disabled={disabled}>{action}</button>}</div>
}

function Empty({ title, description, action, onAction }: { title: string; description: string; action?: string; onAction?: () => void }) {
  return <section className="empty-state"><div className="empty-mark" aria-hidden="true"><span /><span /><span /></div><h2>{title}</h2><p>{description}</p>{action && onAction && <button className="secondary" type="button" onClick={onAction}>{action} <Arrow /></button>}</section>
}
