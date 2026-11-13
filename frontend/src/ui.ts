import type { Evidence } from './types'

export const navigation = [
  ['overview', 'Overview'],
  ['ask', 'Ask Documents'],
  ['rag', 'RAG Workspace'],
  ['ocr', 'OCR'],
  ['library', 'Document Library'],
  ['evidence', 'Evidence Explorer'],
  ['graph', 'Evidence Graph'],
] as const

export type Panel = typeof navigation[number][0]

export function panelFromHash(hash: string): Panel {
  const name = hash.replace(/^#/, '')
  return navigation.some(([id]) => id === name) ? name as Panel : 'overview'
}

export function documentName(sourcePath: string, fallback: string): string {
  return sourcePath.split(/[\\/]/).filter(Boolean).at(-1) || fallback
}

export function locationLabel(item: Evidence): string {
  return item.location_number != null
    ? `${item.location_type || 'Section'} ${item.location_number}`
    : 'Source excerpt'
}

export function retrievalLabel(mode: string): string {
  if (mode === 'hybrid_rrf') return 'Hybrid retrieval'
  if (mode === 'bm25_fallback') return 'Keyword fallback'
  if (mode === 'bm25_only') return 'Keyword retrieval'
  return 'Document retrieval'
}

export function applyTheme(theme: 'light' | 'dark'): void {
  document.documentElement.dataset.theme = theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#191d1a' : '#ffffff')
}
