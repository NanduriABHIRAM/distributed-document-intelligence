/** Shared request handling: HTTP errors, timeouts and caller cancellation. */
export async function request<T>(path: string, options: RequestInit = {}, timeout = 15_000): Promise<T> {
  const controller = new AbortController()
  let timedOut = false
  const abort = () => controller.abort()
  if (options.signal?.aborted) controller.abort()
  options.signal?.addEventListener('abort', abort, { once: true })
  const timer = setTimeout(() => { timedOut = true; controller.abort() }, timeout)

  try {
    const response = await fetch(`/api${path}`, { ...options, signal: controller.signal })
    if (!response.ok) {
      if (response.status === 422) throw new Error('Please enter a question between 2 and 500 characters.')
      throw new Error('The service could not complete this request. Please try again.')
    }
    return await response.json() as T
  } catch (error) {
    if (timedOut) throw new Error('The request took too long. Please try again.')
    if (controller.signal.aborted) throw new DOMException('Request cancelled', 'AbortError')
    if (error instanceof TypeError || error instanceof SyntaxError) {
      throw new Error('Cannot reach the document service. Check that the backend is running, then retry.')
    }
    throw error
  } finally {
    clearTimeout(timer)
    options.signal?.removeEventListener('abort', abort)
  }
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}
