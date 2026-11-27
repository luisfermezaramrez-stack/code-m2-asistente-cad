/**
 * Backend simulado de los E2E (SPEC-042 RF-4, RNF-1).
 *
 * Reutiliza la forma de eventos SSE de `frontend/tests/fakeCadService.ts`, pero
 * aquí se instala como intercepción de red de Playwright sobre las rutas reales
 * `/v1`: la SPA corre sin cambios y sin backend, sin API key y sin GPU.
 */
import type { Page, Route } from '@playwright/test'
import type { Format, Job, Stage } from '../../src/api'

export const SOLICITUD_ID = 'job1'
export const TOKEN_DESCARGA = 'token-simulado-hu41'

/** Un evento SSE con la misma forma que los del doble de Vitest. */
export function event(state: Stage, sequence: number, extra: Partial<Job> = {}): Job {
  return {
    solicitud_id: SOLICITUD_ID,
    estado: state,
    secuencia: sequence,
    terminal: ['verificado', 'declinado', 'error', 'cancelado'].includes(state),
    cancelacion_solicitada: false,
    ...extra,
  }
}

export interface Escenario {
  /** Eventos SSE que el backend entrega en orden, sin esperas fijas. */
  frames: Job[]
  /** Artefactos disponibles; por defecto los tres que anuncia un verificado. */
  archivos?: Format[]
}

/** Petición recibida por el backend simulado; sostiene las aserciones de entrega. */
export interface Peticion {
  method: string
  path: string
  token?: string
}

export class BackendSimulado {
  readonly peticiones: Peticion[] = []
  private readonly frames: Job[]
  private readonly archivos: Set<Format>

  constructor(escenario: Escenario) {
    this.frames = escenario.frames
    this.archivos = new Set(escenario.archivos ?? ['step', 'glb', 'csv'])
  }

  /** Cuerpo SSE completo: el parser del cliente lo divide por líneas en blanco. */
  get cuerpoSse(): string {
    return this.frames
      .map((frame) => `id: ${frame.solicitud_id}:${frame.secuencia}\nevent: ${frame.estado}\ndata: ${JSON.stringify(frame)}\n\n`)
      .join('')
  }

  get descargas(): string[] {
    return this.peticiones
      .filter((peticion) => peticion.method === 'GET' && peticion.path.includes('/archivos/'))
      .map((peticion) => peticion.path.split('/').at(-1) ?? '')
  }

  async instalar(page: Page): Promise<void> {
    await page.route('**/v1/**', (route) => this.atender(route))
  }

  private async atender(route: Route): Promise<void> {
    const peticion = route.request()
    const path = new URL(peticion.url()).pathname
    const method = peticion.method()
    const token = peticion.headers()['x-download-token']
    this.peticiones.push(token ? { method, path, token } : { method, path })

    if (path === '/v1/auth/me') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ requerido: false, autenticado: false, usuario: null }),
      })
      return
    }

    if (path === '/v1/generar' && method === 'POST') {
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-store',
          'X-Download-Token': TOKEN_DESCARGA,
          'X-Solicitud-ID': SOLICITUD_ID,
        },
        body: this.cuerpoSse,
      })
      return
    }

    if (path === `/v1/generaciones/${SOLICITUD_ID}`) {
      const actual = this.frames.at(-1)
      if (!actual) {
        await route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"Escenario sin eventos"}' })
        return
      }
      await route.fulfill({
        status: method === 'DELETE' ? 202 : 200,
        contentType: 'application/json',
        body: JSON.stringify(actual),
      })
      return
    }

    const archivo = /\/archivos\/(step|glb|csv)$/.exec(path)?.[1] as Format | undefined
    if (archivo) {
      const disponible = this.archivos.has(archivo)
      await route.fulfill({
        status: disponible ? 200 : 404,
        contentType: 'application/octet-stream',
        body: method === 'HEAD' ? undefined : 'archivo simulado',
      })
      return
    }

    // Una ruta no prevista no puede pasar en silencio: la UI mostrará el error y
    // el escenario fallará en su aserción.
    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ detail: `Ruta simulada no disponible: ${method} ${path}` }),
    })
  }
}

/** Instala el backend simulado y lo devuelve para inspeccionar sus peticiones. */
export async function servirBackend(page: Page, escenario: Escenario): Promise<BackendSimulado> {
  const backend = new BackendSimulado(escenario)
  await backend.instalar(page)
  return backend
}
