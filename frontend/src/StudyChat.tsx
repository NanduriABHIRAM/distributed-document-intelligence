import { Fragment, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { request, errorMessage } from './api'
import { documentName, locationLabel } from './ui'
import type { Evidence, Retrieval } from './types'

type Reply = {
  query: string
  answer: { document_answer: string; general_answer: string; message: string; citation_status: string }
  evidence: Evidence[]
  retrieval: Retrieval
}
type Turn = { id: number; question: string; reply: Reply }

function Notes({ text, onCitation }: { text: string; onCitation?: (id: string) => void }) {
  function inline(value: string): ReactNode {
    return value.split(/(\*\*[^*]+\*\*|\[E\d+\])/g).map((part, index) =>
      part.startsWith('**') && part.endsWith('**') ? <strong key={index}>{part.slice(2, -2)}</strong>
      : /^\[E\d+\]$/.test(part) && onCitation ? <button key={index} className="reference" onClick={() => onCitation(part.slice(1, -1))} aria-label={`Read source ${part.slice(1, -1)}`}>{part}</button>
      : <Fragment key={index}>{part}</Fragment>)
  }
  const lines = text.split('\n')
  const blocks: ReactNode[] = []
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index].trim()
    if (!line) continue
    if (/^#{1,6}\s/.test(line)) { blocks.push(<h3 key={index}>{inline(line.replace(/^#{1,6}\s+/, ''))}</h3>); continue }
    const listType = /^[-*+]\s/.test(line) ? 'ul' : /^\d+[.)]\s/.test(line) ? 'ol' : null
    if (listType) {
      const start = index
      const items: ReactNode[] = []
      const pattern = listType === 'ul' ? /^[-*+]\s+/ : /^\d+[.)]\s+/
      while (index < lines.length && pattern.test(lines[index].trim())) {
        items.push(<li key={index}>{inline(lines[index].trim().replace(pattern, ''))}</li>); index++
      }
      index--
      blocks.push(listType === 'ul' ? <ul key={start}>{items}</ul> : <ol key={start}>{items}</ol>)
    } else blocks.push(<p key={index}>{inline(line)}</p>)
  }
  return <div className="study-notes">{blocks}</div>
}

function AssistantReply({ turn }: { turn: Turn }) {
  const [selected, setSelected] = useState<string | null>(null)
  const sources = useRef<HTMLDetailsElement>(null)
  const { answer, evidence } = turn.reply
  function openSource(id: string) {
    setSelected(id)
    if (sources.current) sources.current.open = true
    requestAnimationFrame(() => document.getElementById(`chat-${turn.id}-${id}`)?.focus())
  }
  return <article className="chat-assistant" aria-label="Study assistant reply">
    <div className="chat-role">TraceRAG · Study assistant</div>
    {answer.document_answer && <><div className="answer-kicker">From your documents</div><Notes text={answer.document_answer} onCitation={openSource} /><p className="field-note">AI synthesis with checked source references; paraphrases are not independently verified.</p></>}
    {answer.general_answer && <section className="general-notes"><div className="answer-kicker">General knowledge · not from your documents</div><Notes text={answer.general_answer} /></section>}
    {answer.message && <p>{answer.message}</p>}
    {evidence.length > 0 && <details ref={sources} className="chat-sources"><summary>View {evidence.length} retrieved source passages</summary>{evidence.map(item => <article key={item.evidence_id} id={`chat-${turn.id}-${item.evidence_id}`} tabIndex={-1} className={selected === item.evidence_id ? 'selected' : ''}><h4>[{item.evidence_id}] {documentName(item.source_path, item.document_id)}</h4><small>{locationLabel(item)}</small><p>{item.text}</p></article>)}</details>}
  </article>
}

export function StudyChat() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [query, setQuery] = useState('')
  const [style, setStyle] = useState('notes')
  const [topK, setTopK] = useState(6)
  const [allowGeneral, setAllowGeneral] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const active = useRef<AbortController | null>(null)
  const sequence = useRef(0)
  const latest = useRef<HTMLDivElement>(null)
  useEffect(() => () => active.current?.abort(), [])
  useEffect(() => { if (turns.length) latest.current?.scrollIntoView({ block: 'nearest' }) }, [turns.length])

  function cancel() { active.current?.abort(); active.current = null; setBusy(false) }
  async function send() {
    const question = query.trim()
    if (busy || question.length < 2 || question.length > 500) return
    const controller = new AbortController()
    active.current = controller
    setBusy(true); setError('')
    const history = turns.slice(-4).flatMap(turn => [
      { role: 'user', content: turn.question },
      { role: 'assistant', content: [turn.reply.answer.document_answer, turn.reply.answer.general_answer, turn.reply.answer.message].filter(Boolean).join('\n\n').slice(0, 4000) },
    ])
    try {
      const reply = await request<Reply>('/investigations/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ query: question, history, style, top_k: topK, allow_general: allowGeneral }),
      }, 150_000)
      if (!controller.signal.aborted) { setTurns(previous => [...previous, { id: ++sequence.current, question, reply }]); setQuery('') }
    } catch (error) { if (!controller.signal.aborted) setError(errorMessage(error)) }
    finally { if (active.current === controller) { active.current = null; setBusy(false) } }
  }

  return <section className="page study-page">
    <div className="page-heading"><div className="eyebrow">RAG study chat</div><h1>Your documents. Explained.</h1><p>Turn course material into revision notes, clear summaries, and step-by-step explanations. Ask follow-up questions as you study.</p></div>
    <div className="study-toolbar">
      <label>Answer format<select value={style} onChange={event => setStyle(event.target.value)}><option value="notes">Revision notes</option><option value="summary">Short summary</option><option value="explain">Explain step by step</option></select></label>
      <label>Source passages<select value={topK} onChange={event => setTopK(Number(event.target.value))}>{[3, 6, 10, 20].map(value => <option key={value}>{value}</option>)}</select></label>
      <label className="knowledge-toggle"><input type="checkbox" checked={allowGeneral} onChange={event => setAllowGeneral(event.target.checked)} /> Include general knowledge</label>
      <button className="secondary" type="button" onClick={() => { cancel(); setTurns([]); setQuery(''); setError('') }}>New chat</button>
    </div>
    <p className="field-note">{allowGeneral ? 'Additional explanations and examples are labeled separately from document-based notes.' : 'Answers will use your documents only.'} Chat stays in this tab and resets when the page is reloaded.</p>
    {!turns.length && !busy && <div className="study-welcome"><h2>What are you studying today?</h2><div className="suggestions">{['Make revision notes on process scheduling', 'Explain the difference between a process and a thread', 'Summarize the main types of operating systems'].map(example => <button key={example} onClick={() => setQuery(example)}>{example}</button>)}</div></div>}
    <div className="chat-thread">{turns.map(turn => <div className="chat-turn" key={turn.id}><div className="chat-user"><span className="chat-role">You</span><p>{turn.question}</p></div><AssistantReply turn={turn} /></div>)}<div ref={latest} /></div>
    {busy && <div className="loading-state" role="status"><span className="pulse" /><p>Preparing your {style === 'notes' ? 'study notes' : style === 'summary' ? 'summary' : 'explanation'}…</p><button className="text-button" onClick={cancel}>Cancel</button></div>}
    {error && <div className="notice" role="alert"><p>{error}</p><button className="text-button" onClick={() => void send()}>Retry</button></div>}
    <form className="chat-composer" onSubmit={event => { event.preventDefault(); void send() }}>
      <label className="sr-only" htmlFor="study-question">Your question or follow-up</label>
      <textarea id="study-question" value={query} disabled={busy} onChange={event => setQuery(event.target.value)} placeholder={turns.length ? 'Ask a follow-up: explain it more simply, give examples…' : 'Ask for notes, a summary, or an explanation…'} minLength={2} maxLength={500} required rows={3} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void send() } }} />
      <div><span>Enter to send · Shift + Enter for a new line</span><button className="primary" disabled={busy || query.trim().length < 2}>Send question</button></div>
    </form>
    <p className="sr-only" role="status">{turns.length ? `${turns.length} replies in this chat.` : ''}</p>
  </section>
}
