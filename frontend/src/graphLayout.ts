import type { GraphNode, GraphEdge } from './types'

/** Place connected components together, with enough space for readable labels. */
export function layoutGraph(nodes: GraphNode[], edges: GraphEdge[]) {
  const adjacency = new Map(nodes.map(node => [node.id, new Set<string>()]))
  for (const edge of edges) {
    adjacency.get(edge.source)?.add(edge.target)
    adjacency.get(edge.target)?.add(edge.source)
  }
  const visited = new Set<string>()
  const ordered: string[] = []
  for (const node of [...nodes].sort((a, b) => (adjacency.get(b.id)?.size || 0) - (adjacency.get(a.id)?.size || 0))) {
    if (visited.has(node.id)) continue
    const queue = [node.id]
    visited.add(node.id)
    for (let index = 0; index < queue.length; index++) {
      const id = queue[index]
      ordered.push(id)
      for (const neighbor of adjacency.get(id) || []) {
        if (!visited.has(neighbor) && adjacency.has(neighbor)) { visited.add(neighbor); queue.push(neighbor) }
      }
    }
  }
  const columns = Math.max(3, Math.ceil(Math.sqrt(nodes.length * 1.4)))
  const positions = Object.fromEntries(ordered.map((id, index) => [id, {
    x: 100 + (index % columns) * 180,
    y: 80 + Math.floor(index / columns) * 130,
  }]))
  return { positions, width: Math.max(720, columns * 180 + 20), height: Math.max(490, Math.ceil(nodes.length / columns) * 130 + 30) }
}
