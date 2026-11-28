import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, type Router } from 'vue-router'
import App from '../src/App.vue'
import type { PlantillaPublica, RespuestaInstancia } from '../src/generated/api'
import { createAppRouter } from '../src/router'
import TemplatesView from '../src/views/TemplatesView.vue'
import { FakeCadService } from './fakeCadService'

const PLACA: PlantillaPublica = {
  id: 'placa-con-agujeros',
  nombre: 'Placa con agujeros',
  descripcion: 'Placa rectangular con una corona de agujeros pasantes.',
  tipo: 'plate',
  familia: 'plate',
  origen: 'catalogo',
  parametros: [
    { nombre: 'width', etiqueta: 'Ancho', unidad: 'mm', defecto: 100, minimo: 20, maximo: 300, entero: false },
    { nombre: 'thick', etiqueta: 'Espesor', unidad: 'mm', defecto: 6, minimo: 2, maximo: 50, entero: false },
    { nombre: 'bolt_count', etiqueta: 'Agujeros', unidad: 'u', defecto: 4, minimo: 2, maximo: 8, entero: true, valores: [2, 4, 6, 8] },
  ],
}
const MIA: PlantillaPublica = {
  id: 'f'.repeat(32),
  nombre: 'Mi espaciador',
  descripcion: 'Plantilla guardada desde una pieza de tipo spacer.',
  tipo: 'spacer',
  familia: 'spacer',
  origen: 'guardada',
  parametros: [{ nombre: 'od', etiqueta: 'od', unidad: 'mm', defecto: 20, minimo: 10, maximo: 30, entero: false }],
}
const PIEZA: RespuestaInstancia = {
  solicitud_id: 'c'.repeat(32),
  step: 'outputs/x/pieza.step',
  glb: 'outputs/x/pieza.glb',
  bom_csv: 'outputs/x/pieza.csv',
  aviso: 'Diseño preliminar: requiere revisión profesional.',
  volumen_mm3: '17520.00',
  caja_mm: '60.00x50.00x6.00',
  tiempo_generacion_s: '0.000',
  tiempo_construccion_s: '0.420',
  firma: { volume: 17520, area: 7000, bbox_sorted: [6, 50, 60], n_solids: 1, n_faces: 14, n_edges: 36 },
}
const RANGO = 'el parámetro «thick» (Espesor) debe estar entre 2 y 50 mm; recibí 1'

let wrapper: VueWrapper | undefined
let router: Router

afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  document.body.innerHTML = ''
  vi.unstubAllGlobals()
})

function servidor(instancia: () => Response) {
  const fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = String(input)
    if (url === '/v1/plantillas' && !init?.method) return Response.json({ plantillas: [PLACA, MIA] })
    if (url === '/v1/plantillas/placa-con-agujeros/instanciar') return instancia()
    throw new Error(`Servicio simulado sin ruta: ${url}`)
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

async function montarVista() {
  router = createAppRouter(createMemoryHistory())
  await router.push('/plantillas')
  await router.isReady()
  wrapper = mount(TemplatesView, { attachTo: document.body, global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

async function elegirPlaca(vista: VueWrapper) {
  await vista.get('[data-test="plantilla-placa-con-agujeros"] button').trigger('click')
}

describe('HU-49 · RF-5 · lista y formulario de plantillas', () => {
  it('lista el catálogo y las guardadas con nombre, descripción y origen', async () => {
    servidor(() => Response.json(PIEZA))
    const vista = await montarVista()

    const items = vista.findAll('li.plantilla')
    expect(items).toHaveLength(2)
    expect(items[0]!.text()).toContain('Placa con agujeros')
    expect(items[0]!.text()).toContain('Placa rectangular con una corona de agujeros pasantes.')
    expect(items[0]!.text()).toContain('Catálogo')
    expect(items[1]!.text()).toContain('Mi espaciador')
    expect(items[1]!.text()).toContain('Guardada por ti')
  })

  it('al elegir una plantilla muestra un campo etiquetado por parámetro, con rango y unidad', async () => {
    servidor(() => Response.json(PIEZA))
    const vista = await montarVista()
    await elegirPlaca(vista)

    const espesor = vista.get('input#parametro-thick')
    expect(espesor.attributes('type')).toBe('number')
    expect(espesor.attributes('min')).toBe('2')
    expect(espesor.attributes('max')).toBe('50')
    expect((espesor.element as HTMLInputElement).value).toBe('6')
    expect(vista.get('label[for="parametro-thick"]').text()).toBe('Espesor (mm)')
    expect(vista.get(`#${espesor.attributes('aria-describedby')}`).text()).toBe('Entre 2 y 50 mm.')
    // Con valores permitidos se elige de una lista, no se escribe.
    const agujeros = vista.get('select#parametro-bolt_count')
    expect(agujeros.findAll('option').map((opcion) => opcion.text())).toEqual(['2', '4', '6', '8'])
    expect(vista.get('label[for="parametro-bolt_count"]').text()).toBe('Agujeros (u)')
  })
})

describe('HU-49 · AC1/AC2 · generar desde la plantilla', () => {
  it('muestra el mensaje del servidor que nombra el parámetro y su rango ante un 422', async () => {
    const fetch = servidor(() => Response.json({ detail: RANGO }, { status: 422 }))
    const vista = await montarVista()
    await elegirPlaca(vista)
    await vista.get('input#parametro-thick').setValue('1')

    await vista.get('form.parametros').trigger('submit')
    await flushPromises()

    const alerta = vista.get('[data-test="error-plantilla"]')
    expect(alerta.attributes('role')).toBe('alert')
    expect(alerta.text()).toBe(RANGO)
    expect(vista.find('[data-test="resultado-plantilla"]').exists()).toBe(false)
    const [, init] = fetch.mock.calls.at(-1)!
    expect(init?.method).toBe('POST')
    expect(JSON.parse(String(init?.body))).toEqual({ valores: { width: 100, thick: 1, bolt_count: 4 } })
  })

  it('muestra volumen, caja y el enlace a la solicitud cuando la pieza se entrega', async () => {
    servidor(() => Response.json(PIEZA))
    const vista = await montarVista()
    await elegirPlaca(vista)
    await vista.get('input#parametro-width').setValue('60')

    await vista.get('form.parametros').trigger('submit')
    await flushPromises()

    expect(vista.find('[data-test="error-plantilla"]').exists()).toBe(false)
    expect(vista.get('[data-test="volumen"]').text()).toBe('17520.00 mm³')
    expect(vista.get('[data-test="caja"]').text()).toBe('60.00x50.00x6.00 mm')
    expect(vista.get('[data-test="ver-solicitud"]').attributes('href')).toBe(`/historial/${'c'.repeat(32)}`)
  })
})

describe('HU-49 · RF-3 · guardar una solicitud entregada como plantilla', () => {
  const CONSTRUIDA = 'a'.repeat(32)

  async function montarDetalle(guardar: (body: unknown) => Response) {
    const service = new FakeCadService()
    service.registros = [
      { id: CONSTRUIDA, hora: '2025-02-02T09:00:00+00:00', texto: 'Placa de acero de 100 mm', estado: 'construida' },
    ]
    const fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      if (String(input) === '/v1/plantillas' && init?.method === 'POST') return guardar(JSON.parse(String(init.body)))
      return service.fetch(input, init)
    })
    vi.stubGlobal('fetch', fetch)
    router = createAppRouter(createMemoryHistory())
    await router.push(`/historial/${CONSTRUIDA}`)
    await router.isReady()
    wrapper = mount(App, {
      attachTo: document.body,
      global: { plugins: [router], stubs: { GlbViewer: { template: '<div />' } } },
    })
    await flushPromises()
    return { vista: wrapper, fetch }
  }

  it('envía el nombre y anuncia la plantilla guardada', async () => {
    const cuerpos: unknown[] = []
    const { vista } = await montarDetalle((body) => {
      cuerpos.push(body)
      return Response.json({ ...MIA, nombre: 'Mi placa' })
    })

    await vista.get('input#nombre-plantilla').setValue('  Mi placa ')
    await vista.get('form.guardar-plantilla').trigger('submit')
    await flushPromises()

    expect(cuerpos).toEqual([{ solicitud_id: CONSTRUIDA, nombre: 'Mi placa' }])
    const aviso = vista.get('[data-test="plantilla-guardada"]')
    expect(aviso.attributes('role')).toBe('status')
    expect(aviso.text()).toContain('Plantilla «Mi placa» guardada.')
    expect(aviso.get('a').attributes('href')).toBe('/plantillas')
  })

  it('muestra el error del servidor como alerta accesible', async () => {
    const { vista } = await montarDetalle(() => Response.json(
      { detail: 'La pieza de tipo «pipe» no tiene plantilla de catálogo' },
      { status: 422 },
    ))

    await vista.get('input#nombre-plantilla').setValue('Tubo')
    await vista.get('form.guardar-plantilla').trigger('submit')
    await flushPromises()

    const alerta = vista.get('[data-test="error-guardar-plantilla"]')
    expect(alerta.attributes('role')).toBe('alert')
    expect(alerta.text()).toBe('La pieza de tipo «pipe» no tiene plantilla de catálogo')
    expect(vista.find('[data-test="plantilla-guardada"]').exists()).toBe(false)
  })

  it('no envía un nombre vacío', async () => {
    const { vista, fetch } = await montarDetalle(() => Response.json(MIA))

    await vista.get('form.guardar-plantilla').trigger('submit')
    await flushPromises()

    expect(vista.get('[data-test="error-guardar-plantilla"]').text()).toBe('Escribe un nombre para la plantilla.')
    expect(fetch.mock.calls.some(([url, init]) => String(url) === '/v1/plantillas' && init?.method === 'POST')).toBe(false)
  })
})
