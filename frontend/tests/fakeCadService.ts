/** Doble explícito de FastAPI para pruebas. Nunca se importa desde src/. */
import { vi } from 'vitest'
import type { Format, Job, Stage } from '../src/api'

export function event(state: Stage, sequence: number, extra: Partial<Job> = {}): Job {
  return {
    solicitud_id: 'job1', estado: state, secuencia: sequence,
    terminal: ['verificado', 'declinado', 'error', 'cancelado'].includes(state),
    cancelacion_solicitada: false, ...extra,
  }
}

export class FakeCadService {
  current: Job = { solicitud_id: 'job1', estado: 'iniciando', terminal: false, cancelacion_solicitada: false }
  files = new Set<Format>(['step', 'glb', 'csv'])
  posts: { body: unknown; signal: AbortSignal; controller: ReadableStreamDefaultController<Uint8Array> }[] = []
  deleteResult: Job | undefined
  postStatus = 200
  postDetail: unknown = 'Solicitud inválida'
  getStatus = 200
  fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = String(input)
    if (url === '/generar') {
      if (this.postStatus !== 200) return Response.json({ detail: this.postDetail }, { status: this.postStatus })
      const signal = init?.signal as AbortSignal
      const body = new ReadableStream<Uint8Array>({ start: (controller) => {
        this.posts.push({ controller, signal, body: JSON.parse(String(init?.body)) })
        signal.addEventListener('abort', () => {
          try { controller.error(new DOMException('Aborted', 'AbortError')) } catch { /* cerrado */ }
        })
      } })
      return new Response(body, { headers: { 'Content-Type': 'text/event-stream', 'X-Solicitud-ID': 'job1' } })
    }
    if (url.endsWith('/archivos/step') || url.endsWith('/archivos/glb') || url.endsWith('/archivos/csv')) {
      const format = url.split('/').at(-1) as Format
      return new Response(init?.method === 'HEAD' ? null : 'archivo simulado', { status: this.files.has(format) ? 200 : 404 })
    }
    if (url === '/generaciones/job1') {
      if (init?.method === 'DELETE') {
        this.current = this.deleteResult ?? { ...this.current, cancelacion_solicitada: true }
        return Response.json(this.current, { status: this.current.terminal ? 200 : 202 })
      }
      return Response.json(this.current, { status: this.getStatus })
    }
    throw new Error(`Servicio simulado sin ruta: ${url}`)
  })

  send(job: Job, fragmented = false) {
    this.current = job
    const frame = new TextEncoder().encode(`id: ${job.solicitud_id}:${job.secuencia}\nevent: ${job.estado}\ndata: ${JSON.stringify(job)}\n\n`)
    const controller = this.posts.at(-1)!.controller
    if (fragmented) for (const byte of frame) controller.enqueue(Uint8Array.of(byte))
    else controller.enqueue(frame)
  }
  close() { this.posts.at(-1)!.controller.close() }
}
