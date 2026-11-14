import { describe, expect, it } from 'vitest'
import { readSSE } from '../src/sse'

function bytes(chunks: Uint8Array[]) {
  return new ReadableStream<Uint8Array>({ start(controller) {
    chunks.forEach((chunk) => controller.enqueue(chunk)); controller.close()
  } })
}

describe('SSE incremental (bytes de prueba, sin servicios externos)', () => {
  it('conserva UTF-8 y CRLF fragmentados byte a byte, comentarios y data multilínea', async () => {
    const source = ': keep-alive\r\nid: job:1\r\nevent: validando\r\ndata: {"motivo":\r\ndata: "válido"}\r\n\r\n'
    const encoded = new TextEncoder().encode(source)
    const events = []
    for await (const frame of readSSE(bytes([...encoded].map((value) => Uint8Array.of(value))))) events.push(frame)
    expect(events).toEqual([{ id: 'job:1', event: 'validando', data: '{"motivo":\n"válido"}' }])
  })

  it('procesa varios frames por fragmento y delimitadores CR o LF', async () => {
    const events = []
    for await (const frame of readSSE(bytes([new TextEncoder().encode('data: uno\r\rdata: dos\n\n')]))) events.push(frame.data)
    expect(events).toEqual(['uno', 'dos'])
  })

  it('no convierte un EOF incompleto ni un heartbeat en progreso', async () => {
    const events = []
    for await (const frame of readSSE(bytes([new TextEncoder().encode(': vivo\n\ndata: incompleto\n')]))) events.push(frame)
    expect(events).toEqual([])
  })

  it('rechaza UTF-8 inválido', async () => {
    await expect(async () => { for await (const _frame of readSSE(bytes([Uint8Array.of(0xff)]))) { /* consumir */ } }).rejects.toThrow()
  })

  it('libera y cancela el reader cuando el consumidor deja de leer', async () => {
    let cancelled = false
    const stream = new ReadableStream<Uint8Array>({
      start(controller) { controller.enqueue(new TextEncoder().encode('data: uno\n\n')) },
      cancel() { cancelled = true },
    })
    for await (const _frame of readSSE(stream)) break
    expect(cancelled).toBe(true)
    expect(stream.locked).toBe(false)
  })
})
