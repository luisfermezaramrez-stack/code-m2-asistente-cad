export type Stage = 'iniciando' | 'validando' | 'generando' | 'verificado' | 'declinado' | 'error' | 'cancelado'
export interface Job {
  solicitud_id: string
  estado: Stage
  terminal: boolean
  cancelacion_solicitada: boolean
  secuencia?: number
  resultado?: Record<string, string>
  motivo?: string
  codigo_http?: number
  pipeline_detenido?: boolean
  cancelacion_remota_confirmada?: boolean
}
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

export async function availableArtifacts(id: string, result: Record<string, string>, signal: AbortSignal): Promise<Artifact[]> {
  const formats: Format[] = ['step', 'glb', 'csv']
  const found = await Promise.all(formats.map(async (format) => {
    if (!(format === 'csv' ? result.bom_csv || result.csv : result[format])) return null
    const url = artifactUrl(id, format)
    try {
      const response = await fetch(url, { method: 'HEAD', signal })
      return response.ok ? { format, url } : null
    } catch (error) {
      if (signal.aborted) throw error
      return null
    }
  }))
  return found.filter((item): item is Artifact => item !== null)
}
