/** Doble explícito de FastAPI para pruebas. Nunca se importa desde src/. */
import { vi } from 'vitest'
import type { Format, Job, Stage } from '../src/api'
import type { EstadoSesion } from '../src/auth'
import type { RegistroResumen } from '../src/generated/api'

/** Token de descarga que el servicio simulado emite para una solicitud anterior (HU-37). */
export const TOKEN_HISTORIAL = 'token-simulado-hu37'

function cabecera(init: RequestInit | undefined, nombre: string): string {
  return new Headers(init?.headers).get(nombre) ?? ''
}

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
  sesion: EstadoSesion = { requerido: false, autenticado: false, usuario: null }
  postStatus = 200
  postDetail: unknown = 'Solicitud inválida'
  getStatus = 200
  registros: RegistroResumen[] = []
  filas: Record<string, Record<string, string>> = {}
  registrosStatus = 200
  esperaRegistros: Promise<void> | undefined
  fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = String(input)
    if (url === '/v1/auth/me') return Response.json(this.sesion)
    if (url === '/v1/auth/login') {
      const { usuario } = JSON.parse(String(init?.body)) as { usuario: string; clave: string }
      this.sesion = { requerido: true, autenticado: true, usuario }
      return Response.json({ autenticado: true, usuario })
    }
    if (url === '/v1/auth/logout') {
      this.sesion = { requerido: true, autenticado: false, usuario: null }
      return Response.json({ autenticado: false })
    }
    if (url === '/v1/generar') {
      if (this.postStatus !== 200) return Response.json({ detail: this.postDetail }, { status: this.postStatus })
      const signal = init?.signal as AbortSignal
      const body = new ReadableStream<Uint8Array>({ start: (controller) => {
        this.posts.push({ controller, signal, body: JSON.parse(String(init?.body)) })
        signal.addEventListener('abort', () => {
          try { controller.error(new DOMException('Aborted', 'AbortError')) } catch { /* cerrado */ }
        })
      } })
      return new Response(body, { headers: { 'Content-Type': 'text/event-stream', 'X-Download-Token': 'token-simulado-hu36', 'X-Solicitud-ID': 'job1' } })
    }
    if (url.endsWith('/archivos/step') || url.endsWith('/archivos/glb') || url.endsWith('/archivos/csv')) {
      const format = url.split('/').at(-1) as Format
      // El trabajo sigue vivo sólo mientras el formato esté en `files` (HEAD responde igual).
      return new Response(init?.method === 'HEAD' ? null : 'archivo simulado', { status: this.files.has(format) ? 200 : 404 })
    }
    if (url === '/v1/registros' || url.startsWith('/v1/registros?')) {
      if (this.esperaRegistros) await this.esperaRegistros
      if (this.registrosStatus !== 200) {
        return Response.json({ detail: 'El historial no está disponible.' }, { status: this.registrosStatus })
      }
      const consulta = new URL(url, 'http://servicio-simulado').searchParams
      const resultado = consulta.get('resultado')
      const texto = consulta.get('texto')
      const registros = this.registros.filter((registro) => (!resultado || registro.estado === resultado)
        && (!texto || registro.texto.toLowerCase().includes(texto.toLowerCase())))
      return Response.json({ registros })
    }
    if (url.startsWith('/v1/registros/')) {
      const resto = url.slice('/v1/registros/'.length)
      if (resto.endsWith('/step')) {
        if (cabecera(init, 'X-Download-Token') !== TOKEN_HISTORIAL) {
          return Response.json({ detail: 'La autorización de descarga es inválida.' }, { status: 403 })
        }
        return new Response('STEP simulado', { headers: { 'Content-Type': 'application/step' } })
      }
      const fila = this.fila(decodeURIComponent(resto))
      if (!fila) return Response.json({ detail: 'Registro no encontrado.' }, { status: 404 })
      return Response.json(fila, { headers: { 'X-Download-Token': TOKEN_HISTORIAL } })
    }
    if (url === '/v1/generaciones/job1') {
      if (init?.method === 'DELETE') {
        this.current = this.deleteResult ?? { ...this.current, cancelacion_solicitada: true }
        return Response.json(this.current, { status: this.current.terminal ? 200 : 202 })
      }
      return Response.json(this.current, { status: this.getStatus })
    }
    throw new Error(`Servicio simulado sin ruta: ${url}`)
  })

  /**
   * Fila del registro tal como la sirve el backend: incluye `estado` y `motivo`
   * ya derivados (RNF-1). Se deriva del resumen si no hay override, para que el
   * doble se parezca al backend real sin que la vista tenga que derivar nada.
   */
  fila(id: string): Record<string, string> | undefined {
    const explicita = this.filas[id]
    if (explicita) return explicita
    const resumen = this.registros.find((registro) => registro.id === id)
    if (!resumen) return undefined
    const declinada = resumen.estado === 'declinada'
    return {
      id: resumen.id,
      hora: resumen.hora,
      texto: resumen.texto,
      traduccion: 'no aplica',
      resultado: resumen.estado === 'construida'
        ? `{'step': 'outputs/${id}/pieza.step', 'glb': 'outputs/${id}/pieza.glb', 'bom_csv': 'outputs/${id}/materiales.csv'}`
        : 'sin resultado',
      latencia_ms: '42',
      error: declinada
        ? (resumen.motivo ?? 'ninguno')
        : resumen.estado === 'error' ? 'No fue posible completar la generación.' : 'ninguno',
      version: 'desconocida',
      usuario: 'ana',
      causa: declinada ? 'familia_no_soportada' : 'ninguna',
      prompt: 'no aplica',
      prompt_hash: 'no aplica',
      estado: resumen.estado,
      motivo: resumen.motivo ?? '',
    }
  }

  send(job: Job, fragmented = false) {
    this.current = job
    const frame = new TextEncoder().encode(`id: ${job.solicitud_id}:${job.secuencia}\nevent: ${job.estado}\ndata: ${JSON.stringify(job)}\n\n`)
    const controller = this.posts.at(-1)!.controller
    if (fragmented) for (const byte of frame) controller.enqueue(Uint8Array.of(byte))
    else controller.enqueue(frame)
  }
  close() { this.posts.at(-1)!.controller.close() }
}
