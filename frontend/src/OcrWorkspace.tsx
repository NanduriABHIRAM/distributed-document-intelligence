import { useEffect, useRef, useState } from 'react'
import { errorMessage, request } from './api'

type Extraction = { pages: { page: number; text: string; method: string }[]; text: string }

export function OcrWorkspace() {
  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState('auto')
  const [result, setResult] = useState<Extraction | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])

  async function extract() {
    if (!file) return
    if (file.size > 20 * 1024 * 1024) { setError('Choose a file smaller than 20 MB.'); return }
    const active = new AbortController()
    controller.current = active
    setBusy(true); setError(''); setResult(null)
    try {
      setResult(await request<Extraction>(`/documents/ocr?filename=${encodeURIComponent(file.name)}&mode=${mode}`, {
        method: 'POST', body: file, headers: { 'Content-Type': 'application/octet-stream' }, signal: active.signal,
      }, 180_000))
    } catch (error) { if (!active.signal.aborted) setError(errorMessage(error)) }
    finally { if (!active.signal.aborted) setBusy(false) }
  }

  function download() {
    if (!result) return
    const url = URL.createObjectURL(new Blob([result.text], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url; link.download = `${file?.name || 'extracted'}.txt`; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return <section className="page">
    <div className="page-heading"><div className="eyebrow">Optical character recognition</div><h1>Turn scans into searchable text.</h1><p>Extract text from a PDF or image, review each page, and download the result for ingestion into your document corpus.</p></div>
    <form className="ocr-form" onSubmit={event => { event.preventDefault(); void extract() }}>
      <label htmlFor="ocr-file">Source document <span>PDF, PNG, or JPEG · up to 20 MB · 50 pages</span></label>
      <input id="ocr-file" type="file" accept=".pdf,.png,.jpg,.jpeg" required disabled={busy} onChange={event => { setFile(event.target.files?.[0] || null); setResult(null); setError('') }} />
      <label htmlFor="ocr-mode">Extraction mode</label>
      <select id="ocr-mode" value={mode} disabled={busy} onChange={event => setMode(event.target.value)}><option value="auto">Automatic — OCR pages without text</option><option value="force">OCR every page — include scanned content</option></select>
      <p className="field-note">OCR uses English recognition. Scanned pages require Tesseract language data on the server. Extraction previews do not automatically change the indexed corpus.</p>
      <button className="primary" disabled={!file || busy}>{busy ? 'Extracting text…' : 'Extract text'}</button>
    </form>
    {busy && <p role="status" className="field-note">Reading pages and recognizing text. Large scans may take a few minutes.</p>}
    {error && <div className="notice" role="alert">{error}</div>}
    {result && <section aria-label="Extracted text"><div className="evidence-header"><h2>{result.pages.length} pages extracted</h2><button className="secondary" onClick={download}>Download text</button></div>{!result.text.trim() && <p className="notice">No readable text was found. Try a clearer scan or OCR every page.</p>}{result.pages.map(page => <article className="ocr-page" key={page.page}><h3>Page {page.page} <span>{page.method === 'ocr' ? 'OCR' : 'Embedded text'}</span></h3><pre>{page.text || 'No text detected on this page.'}</pre></article>)}</section>}
  </section>
}
