export interface SSEFrame { event: string; data: string; id?: string }

/** Parser incremental SSE: UTF-8, CR/LF/CRLF, líneas data múltiples y comentarios. */
export async function* readSSE(body: ReadableStream<Uint8Array>): AsyncGenerator<SSEFrame> {
  const reader = body.getReader()
  const decoder = new TextDecoder('utf-8', { fatal: true })
  let buffer = ''
  let event = 'message'
  let id: string | undefined
  let data: string[] = []
  let complete = false

  function line(value: string): SSEFrame | undefined {
    if (value === '') {
      const frame = data.length ? { event, data: data.join('\n'), id } : undefined
      event = 'message'; data = []
      return frame
    }
    if (value.startsWith(':')) return
    const colon = value.indexOf(':')
    const field = colon < 0 ? value : value.slice(0, colon)
    let text = colon < 0 ? '' : value.slice(colon + 1)
    if (text.startsWith(' ')) text = text.slice(1)
    if (field === 'event') event = text
    if (field === 'data') data.push(text)
    if (field === 'id' && !text.includes('\0')) id = text
  }

  try {
    while (true) {
      const chunk = await reader.read()
      buffer += chunk.done ? decoder.decode() : decoder.decode(chunk.value, { stream: true })
      while (true) {
        const match = /[\r\n]/.exec(buffer)
        if (!match) break
        const at = match.index
        if (buffer[at] === '\r' && at === buffer.length - 1 && !chunk.done) break
        const size = buffer[at] === '\r' && buffer[at + 1] === '\n' ? 2 : 1
        const frame = line(buffer.slice(0, at))
        buffer = buffer.slice(at + size)
        if (frame) yield frame
      }
      if (buffer.length > 1_000_000 || data.join('\n').length > 1_000_000) {
        throw new Error('Respuesta demasiado extensa.')
      }
      if (chunk.done) { complete = true; break }
    }
    // SSE solo despacha frames terminados por una línea vacía; no inventar uno al EOF.
  } finally {
    if (!complete) await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}
