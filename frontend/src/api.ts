import type { ConsultarGeneracionGeneracionesSolicitudIdGetResponse } from './generated/api'

export type Job = ConsultarGeneracionGeneracionesSolicitudIdGetResponse
export type Stage = Job['estado']
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

export function jobUrl(id: string): string { return `/generaciones/${encodeURIComponent(id)}` }
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
