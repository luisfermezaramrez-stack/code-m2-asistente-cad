import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, type Router } from 'vue-router'
import App from '../src/App.vue'
import type { RegistroResumen } from '../src/generated/api'
import { createAppRouter } from '../src/router'
import { FakeCadService, TOKEN_HISTORIAL } from './fakeCadService'

const CONSTRUIDA = 'a'.repeat(32)
const DECLINADA = 'b'.repeat(32)
const MOTIVO = 'Pieza declinada: familia fuera de catálogo.'

const visorSimulado = {
  props: ['url', 'token'],
  template: '<div data-testid="visor-simulado">Visor WebGL simulado: {{ url }}</div>',
}

let service: FakeCadService
let router: Router
let wrapper: VueWrapper | undefined

function solicitudes(): RegistroResumen[] {
  return [
    { id: CONSTRUIDA, hora: '2025-02-02T09:00:00+00:00', texto: 'Placa de acero de 100 mm', estado: 'construida' },
    { id: DECLINADA, hora: '2025-02-01T09:00:00+00:00', texto: 'Soporte soldado de 40 mm', estado: 'declinada', motivo: MOTIVO },
  ]
}

async function montar(ruta = '/historial') {
  router = createAppRouter(createMemoryHistory())
  await router.push(ruta)
  await router.isReady()
  wrapper = mount(App, {
    attachTo: document.body,
    global: { plugins: [router], stubs: { GlbViewer: visorSimulado } },
  })
  await flushPromises()
}

function urls(): string[] {
  return service.fetch.mock.calls.map(([url]) => String(url))
}

function urlsRegistros(): string[] {
  return urls().filter((url) => url.startsWith('/v1/registros'))
}

beforeEach(() => {
  service = new FakeCadService()
  vi.stubGlobal('fetch', service.fetch)
  // jsdom no implementa las URL de objeto que usa la descarga autorizada ni la
  // navegación del ancla con la que el navegador guarda el archivo.
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:historial') })
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  document.body.innerHTML = ''
  window.localStorage.clear()
  vi.unstubAllGlobals()
})

describe('AC3 · El historial usa el endpoint de listado', () => {
  it('pide /v1/registros y pinta las filas del backend sin recorrer ids', async () => {
    // Arrange
    service.registros = solicitudes()

    // Act
    await montar('/historial')

    // Assert
    expect(urls().filter((url) => url.startsWith('/v1/registros'))).toEqual(['/v1/registros'])
    const filas = wrapper!.findAll('li.registro')
    expect(filas).toHaveLength(2)
    expect(filas[0]!.text()).toContain('2025-02-02T09:00:00+00:00')
    expect(filas[0]!.text()).toContain('Placa de acero de 100 mm')
    expect(filas[0]!.text()).toContain('Construida')
    expect(filas[1]!.text()).toContain('Soporte soldado de 40 mm')
    expect(filas[1]!.text()).toContain('Declinada')
    expect(filas[1]!.text()).toContain(MOTIVO)
    expect(wrapper!.find('.estado-vista').exists()).toBe(false)
    expect(wrapper!.findAll('a.reabrir')).toHaveLength(2)
  })
})

describe('AC1 y AC2 · Persistencia del historial en el backend', () => {
  it('recargar y abrir desde otro equipo muestra las mismas solicitudes sin caché local', async () => {
    // Arrange
    service.registros = solicitudes()
    const almacenamiento = JSON.stringify({ ...window.localStorage })

    // Act: primera carga y recarga completa (montaje nuevo contra el mismo backend).
    await montar('/historial')
    const primera = wrapper!.findAll('li.registro').map((fila) => fila.text())
    wrapper!.unmount()
    wrapper = undefined
    await montar('/historial')
    const segunda = wrapper!.findAll('li.registro').map((fila) => fila.text())

    // Assert
    expect(segunda).toEqual(primera)
    expect(segunda).toHaveLength(2)
    expect(JSON.stringify({ ...window.localStorage })).toBe(almacenamiento)
    expect(Object.keys(window.localStorage).filter((clave) => /historial|registro/i.test(clave))).toEqual([])
  })
})

describe('RF-2 · Filtros atendidos por el backend', () => {
  it('filtrar por resultado y por texto vuelve a pedir el listado con esos parámetros', async () => {
    // Arrange
    service.registros = solicitudes()
    await montar('/historial')
    expect(wrapper!.findAll('li.registro')).toHaveLength(2)

    // Act: filtro por resultado.
    await wrapper!.get('select#filtro-resultado').setValue('declinada')
    await wrapper!.get('form.filtros').trigger('submit')
    await flushPromises()

    // Assert
    expect(urlsRegistros().at(-1)).toBe('/v1/registros?resultado=declinada')
    expect(wrapper!.findAll('li.registro')).toHaveLength(1)
    expect(wrapper!.get('li.registro').text()).toContain('Soporte soldado de 40 mm')

    // Act: filtro por texto de la descripción, sin filtro de resultado.
    await wrapper!.get('select#filtro-resultado').setValue('')
    await wrapper!.get('input#filtro-texto').setValue('Placa')
    await wrapper!.get('form.filtros').trigger('submit')
    await flushPromises()

    // Assert
    expect(urlsRegistros().at(-1)).toBe('/v1/registros?texto=Placa')
    expect(wrapper!.findAll('li.registro')).toHaveLength(1)
    expect(wrapper!.get('li.registro').text()).toContain('Placa de acero de 100 mm')
  })
})

describe('S2 · El historial ya no lee ?estado=', () => {
  it('ignora ?estado=error y muestra el listado real del backend', async () => {
    // Arrange
    service.registros = solicitudes()

    // Act
    await montar('/historial?estado=error')

    // Assert
    expect(wrapper!.find('.estado-vista').exists()).toBe(false)
    expect(wrapper!.findAll('li.registro')).toHaveLength(2)
    expect(urlsRegistros()).toEqual(['/v1/registros'])
  })
})

describe('RF-3, RF-4 y AC4 · Reabrir una solicitud', () => {
  it('muestra estado y motivo, descarga el STEP con token y sólo ofrece GLB si el trabajo vive', async () => {
    // Arrange
    service.registros = solicitudes()
    await montar('/historial')

    // Act: reabrir la solicitud declinada.
    await wrapper!.findAll('a.reabrir')[1]!.trigger('click')
    await flushPromises()

    // Assert: estado y motivo, sin STEP ni visor 3D para una declinación.
    expect(router.currentRoute.value.path).toBe(`/historial/${DECLINADA}`)
    expect(wrapper!.text()).toContain('Declinada')
    expect(wrapper!.text()).toContain(MOTIVO)
    expect(wrapper!.find('button[data-download-filename="pieza.step"]').exists()).toBe(false)
    expect(wrapper!.find('[data-testid="visor-simulado"]').exists()).toBe(false)
    expect(urls().filter((url) => url.endsWith('/archivos/glb'))).toEqual([])

    // Act: reabrir la solicitud construida con su trabajo vivo en el servicio.
    await router.push('/historial')
    await flushPromises()
    await wrapper!.findAll('a.reabrir')[0]!.trigger('click')
    await flushPromises()

    // Assert: STEP disponible y visor 3D ofrecido.
    expect(router.currentRoute.value.path).toBe(`/historial/${CONSTRUIDA}`)
    expect(wrapper!.text()).toContain('Construida')
    const descarga = wrapper!.get('button[data-download-filename="pieza.step"]')
    expect(descarga.attributes('data-download-url')).toBe(`/v1/registros/${CONSTRUIDA}/step`)
    expect(urls()).toContain(`/v1/generaciones/${CONSTRUIDA}/archivos/glb`)
    expect(wrapper!.find('[data-testid="visor-simulado"]').exists()).toBe(true)

    // Act: descargar el STEP reabierto.
    await descarga.trigger('click')
    await flushPromises()

    // Assert: la descarga viaja con el token que emitió la consulta.
    const peticion = service.fetch.mock.calls.find(([url]) => String(url) === `/v1/registros/${CONSTRUIDA}/step`)
    expect(peticion).toBeDefined()
    expect(new Headers(peticion![1]?.headers).get('X-Download-Token')).toBe(TOKEN_HISTORIAL)

    // Act: el trabajo deja de estar vivo en el servidor y se reabre otra vez.
    service.files = new Set()
    await router.push('/historial')
    await flushPromises()
    await wrapper!.findAll('a.reabrir')[0]!.trigger('click')
    await flushPromises()

    // Assert: sin GLB ni CSV, el STEP sigue ofreciéndose.
    expect(router.currentRoute.value.path).toBe(`/historial/${CONSTRUIDA}`)
    expect(wrapper!.find('[data-testid="visor-simulado"]').exists()).toBe(false)
    expect(wrapper!.find('button[data-download-filename="pieza.step"]').exists()).toBe(true)
    expect(wrapper!.text()).toContain('La vista 3D de una solicitud anterior')
  })
})

describe('S8 y RNF-1 · El detalle no repite la precedencia del estado', () => {
  it('muestra el estado y el motivo del backend aunque el resultado contenga un STEP', async () => {
    // Arrange: el backend clasifica la fila como declinada aunque su `resultado`
    // lleve un STEP; el cliente no debe derivar otro estado por su cuenta.
    service.registros = solicitudes()
    service.filas[DECLINADA] = {
      id: DECLINADA,
      hora: '2025-02-01T09:00:00+00:00',
      texto: 'Soporte soldado de 40 mm',
      traduccion: 'no aplica',
      resultado: `{'step': 'outputs/${DECLINADA}/pieza.step', 'glb': 'outputs/${DECLINADA}/pieza.glb',`
        + ` 'bom_csv': 'outputs/${DECLINADA}/materiales.csv'}`,
      latencia_ms: '30',
      error: MOTIVO,
      version: 'desconocida',
      usuario: 'ana',
      causa: 'familia_no_soportada',
      prompt: 'no aplica',
      prompt_hash: 'no aplica',
      estado: 'declinada',
      motivo: MOTIVO,
    }

    // Act
    await montar(`/historial/${DECLINADA}`)

    // Assert: gana el estado del backend, no la derivación sobre `resultado`.
    expect(wrapper!.get('.registro-estado').text()).toBe('Declinada')
    expect(wrapper!.text()).toContain(MOTIVO)
    expect(wrapper!.text()).not.toContain('Construida')
    expect(wrapper!.find('button[data-download-filename="pieza.step"]').exists()).toBe(false)
  })
})
