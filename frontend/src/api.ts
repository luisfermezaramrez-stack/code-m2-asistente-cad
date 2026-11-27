import type {
  ConsultarGeneracionV1GeneracionesSolicitudIdGetResponse,
  ListarRegistrosV1RegistrosGetData,
  RegistroResumen,
} from './generated/api'

export type Job = ConsultarGeneracionV1GeneracionesSolicitudIdGetResponse
export type Stage = Job['estado']
// Estados visibles del historial, tal como los deriva el backend (HU-37, RF-2).
export type EstadoRegistro = RegistroResumen['estado']
export type FiltroResultado = NonNullable<ListarRegistrosV1RegistrosGetData['query']>['resultado']
export type { RegistroResumen }
/** Fila completa del registro: `GET /v1/registros/{id}` responde un mapa de texto. */
export type FilaRegistro = Record<string, string>
export interface FiltrosHistorial { resultado?: FiltroResultado; texto?: string | null }
export interface RegistroConsultado { fila: FilaRegistro; token: string }

const ESTADOS: EstadoRegistro[] = ['construida', 'declinada', 'error', 'desconocida']

// Formatos y enlaces descubiertos por HEAD: estado local de UI, no un cuerpo JSON.
export type Format = 'step' | 'glb' | 'csv'
export interface Artifact { format: Format; url: string }
const terminals = new Set<Stage>(['verificado', 'declinado', 'error', 'cancelado'])
const stages = new Set<Stage>(['iniciando', 'validando', 'generando', ...terminals])

export function parseJob(value: unknown): Job {
  if (typeof value !== 'object' || value === null) throw new Error('Respuesta inválida.')
  const job = value as Job
  if (typeof job.solicitud_id !== 'string' || !/^[a-zA-Z0-9_-]{1,128}$/.test(job.solicitud_id)
    || !stages.has(job.estado) || typeof job.terminal !== 'boolean'
    || job.terminal !== terminals.has(job.estado) || typeof job.cancelacion_solicitada !== 'boolean'
    || (job.secuencia !== undefined && (!Number.isInteger(job.secuencia) || job.secuencia < 1))
    || (job.motivo !== undefined && typeof job.motivo !== 'string')
    || (job.resultado !== undefined && (typeof job.resultado !== 'object' || job.resultado === null
      || !Object.values(job.resultado).every((item) => typeof item === 'string')))
    || (job.estado === 'verificado' && !job.resultado)
    || (job.estado === 'cancelado' && job.pipeline_detenido !== true)) {
    throw new Error('Respuesta inválida.')
  }
  return job
}

export function jobUrl(id: string): string { return `/v1/generaciones/${encodeURIComponent(id)}` }
export function artifactUrl(id: string, format: Format): string { return `${jobUrl(id)}/archivos/${format}` }

export function publicMessage(text: unknown, fallback: string): string {
  if (typeof text !== 'string' || !text.trim()) return fallback
  // Excepción exacta del contrato público: solo el nombre de la variable, nunca su valor.
  if (text === 'El modelo no está configurado: falta DEEPSEEK_API_KEY.') return text
  // No mostrar URLs, direcciones del modelo, claves o trazas devueltas por servicios.
  if (/https?:|localhost|127\.|(?:\d{1,3}\.){3}\d{1,3}|api[_ -]?key|bearer|traceback|LLM_BASE_URL|GEMINI_API_KEY/i.test(text)) return fallback
  return text.slice(0, 600)
}

export async function requestJob(id: string, method: 'GET' | 'DELETE', signal: AbortSignal): Promise<Job> {
  const response = await fetch(jobUrl(id), { method, signal, headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(response.status === 404
    ? 'La solicitud ya no está disponible. No se puede confirmar su estado.'
    : 'No se pudo consultar la solicitud. Vuelve a intentarlo.')
  return parseJob(await response.json())
}

export class ArtifactAccessError extends Error {}
export async function availableArtifacts(id: string, result: NonNullable<Job['resultado']>, signal: AbortSignal, token?: string): Promise<Artifact[]> {
  const formats: Format[] = ['step', 'glb', 'csv']
  const found = await Promise.all(formats.map(async (format) => {
    if (!(format === 'csv' ? result.bom_csv || result.csv : result[format])) return null
    const url = artifactUrl(id, format)
    try {
      const response = await fetch(url, { method: 'HEAD', signal, headers: token ? { 'X-Download-Token': token } : undefined })
      if (response.status === 403) throw new ArtifactAccessError('La autorización para consultar archivos no es válida.')
      if (response.status === 410) throw new ArtifactAccessError('Los archivos han expirado. Genera la pieza nuevamente.')
      return response.ok ? { format, url } : null
    } catch (error) {
      if (signal.aborted || error instanceof ArtifactAccessError) throw error
      return null
    }
  }))
  return found.filter((item): item is Artifact => item !== null)
}
/** Descarga autorizada; nunca expone el token en la URL. */
export async function downloadArtifact(artifact: Artifact, token: string): Promise<void> {
  if (!token) throw new Error('La autorización de descarga no está disponible.')
  const response = await fetch(artifact.url, {
    method: 'GET',
    headers: { 'X-Download-Token': token },
    cache: 'no-store',
  })
  if (response.status === 410) throw new Error('El archivo ha expirado. Genera la pieza nuevamente.')
  if (response.status === 403) throw new Error('La autorización de descarga es inválida.')
  if (!response.ok) throw new Error('No se pudo descargar el archivo.')
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  try {
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = `pieza.${artifact.format}`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
  } finally {
    // Retraso para que el navegador pueda comenzar a guardar el archivo.
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
  }
}

/* Historial de solicitudes (HU-37): el backend es la única fuente de verdad (RNF-1). */

export function registrosUrl({ resultado, texto }: FiltrosHistorial = {}): string {
  const consulta = new URLSearchParams()
  if (resultado) consulta.set('resultado', resultado)
  const limpio = texto?.trim()
  if (limpio) consulta.set('texto', limpio)
  const cadena = consulta.toString()
  return cadena ? `/v1/registros?${cadena}` : '/v1/registros'
}

export function registroUrl(id: string): string { return `/v1/registros/${encodeURIComponent(id)}` }
/** STEP de una solicitud anterior: se sirve desde el registro, no desde el trabajo vivo. */
export function stepRegistro(id: string): Artifact { return { format: 'step', url: `${registroUrl(id)}/step` } }

function esResumen(valor: unknown): valor is RegistroResumen {
  if (typeof valor !== 'object' || valor === null) return false
  const resumen = valor as Partial<RegistroResumen>
  return typeof resumen.id === 'string' && typeof resumen.hora === 'string'
    && typeof resumen.texto === 'string' && ESTADOS.includes(resumen.estado as EstadoRegistro)
    && (resumen.motivo === undefined || resumen.motivo === null || typeof resumen.motivo === 'string')
}

/** Valida el listado recibido: una respuesta ambigua nunca se pinta como historial. */
export function parseRegistros(valor: unknown): RegistroResumen[] {
  const registros = (valor as { registros?: unknown } | null)?.registros
  if (!Array.isArray(registros) || !registros.every(esResumen)) {
    throw new Error('No se pudo cargar el historial.')
  }
  return registros
}

export async function listarRegistros(filtros: FiltrosHistorial, signal: AbortSignal): Promise<RegistroResumen[]> {
  const response = await fetch(registrosUrl(filtros), {
    signal,
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  })
  if (!response.ok) throw new Error(await publicDetail(response, 'No se pudo cargar el historial.'))
  let cuerpo: unknown
  try {
    cuerpo = await response.json()
  } catch {
    throw new Error('No se pudo cargar el historial.')
  }
  return parseRegistros(cuerpo)
}

/**
 * Consulta una solicitud anterior y su token de descarga (HU-37, RF-4).
 * Sin el token, su STEP no se puede descargar pasado el reinicio del servidor.
 */
export async function consultarRegistro(id: string, signal: AbortSignal): Promise<RegistroConsultado> {
  const response = await fetch(registroUrl(id), {
    signal,
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  })
  if (response.status === 404) throw new Error('La solicitud ya no está disponible en el historial.')
  if (!response.ok) throw new Error(await publicDetail(response, 'No se pudo consultar la solicitud. Vuelve a intentarlo.'))
  let fila: unknown
  try {
    fila = await response.json()
  } catch {
    throw new Error('No se pudo consultar la solicitud. Vuelve a intentarlo.')
  }
  if (typeof fila !== 'object' || fila === null || Array.isArray(fila)
    || !Object.values(fila).every((valor) => typeof valor === 'string')) {
    throw new Error('No se pudo consultar la solicitud. Vuelve a intentarlo.')
  }
  return { fila: fila as FilaRegistro, token: response.headers.get('X-Download-Token') ?? '' }
}

async function publicDetail(response: Response, fallback: string): Promise<string> {
  try {
    const cuerpo: unknown = await response.json()
    return publicMessage((cuerpo as { detail?: unknown } | null)?.detail, fallback)
  } catch {
    return fallback
  }
}

/**
 * Estado visible de una fila: lo deriva el backend, que es la única fuente de
 * verdad (RNF-1). Aquí sólo se valida el valor recibido; fuera del contrato es
 * `desconocida`, nunca una derivación local.
 */
export function validarEstado(valor: string | undefined): EstadoRegistro {
  return ESTADOS.includes(valor as EstadoRegistro) ? (valor as EstadoRegistro) : 'desconocida'
}

/** GLB de una solicitud anterior: sólo se ofrece mientras el trabajo sigue vivo (RF-4). */
export async function glbVivo(id: string, token: string, signal: AbortSignal): Promise<Artifact | null> {
  const url = artifactUrl(id, 'glb')
  try {
    const response = await fetch(url, {
      method: 'HEAD',
      signal,
      headers: token ? { 'X-Download-Token': token } : undefined,
    })
    return response.ok ? { format: 'glb', url } : null
  } catch (error) {
    if (signal.aborted) throw error
    return null
  }
}
