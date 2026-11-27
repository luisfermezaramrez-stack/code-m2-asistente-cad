import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import MetricsView from '../src/views/MetricsView.vue'

function panorama(extra: Record<string, unknown> = {}) {
  return {
    disponible: true,
    motivo: null,
    desde: '2026-11-26T00:00:00+00:00',
    hasta: '2026-11-27T00:00:00+00:00',
    solicitudes: 9,
    entregadas: 5,
    declinadas: 3,
    errores: 1,
    declinaciones_por_causa: { familia_no_soportada: 2, dimension_incoherente: 1 },
    latencia_media_ms: 1234.5,
    costo_usd: 0.0421,
    mlflow_ui: 'http://127.0.0.1:5000',
    generado_en: '2026-11-27T00:00:00+00:00',
    ...extra,
  }
}

function montarCon(datos: unknown): VueWrapper {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => datos })))
  return mount(MetricsView)
}

describe('AC1 y AC3 · panorama con datos', () => {
  let wrapper: VueWrapper | undefined
  afterEach(() => {
    wrapper?.unmount()
    vi.unstubAllGlobals()
  })

  it('muestra los agregados y el costo acumulado', async () => {
    wrapper = montarCon(panorama())
    await flushPromises()

    expect(wrapper.get('[data-test="solicitudes"]').text()).toBe('9')
    expect(wrapper.get('[data-test="entregadas"]').text()).toBe('5')
    expect(wrapper.get('[data-test="declinadas"]').text()).toBe('3')
    expect(wrapper.get('[data-test="latencia"]').text()).toBe('1235 ms')
    expect(wrapper.get('[data-test="costo"]').text()).toBe('USD 0.0421')
    expect(wrapper.text()).toContain('familia_no_soportada')
  })

  it('enlaza a la UI de MLflow para el detalle por corrida', async () => {
    wrapper = montarCon(panorama())
    await flushPromises()

    const enlace = wrapper.get('[data-test="mlflow"]')
    expect(enlace.attributes('href')).toBe('http://127.0.0.1:5000')
    expect(enlace.attributes('rel')).toContain('noopener')
  })
})

describe('AC2 · estado degradado', () => {
  let wrapper: VueWrapper | undefined
  afterEach(() => {
    wrapper?.unmount()
    vi.unstubAllGlobals()
  })

  it('muestra el motivo y no se rompe cuando MLflow no responde', async () => {
    wrapper = montarCon(
      panorama({
        disponible: false,
        motivo: 'El seguimiento está desactivado: activa MLFLOW y vuelve a intentarlo.',
        solicitudes: 0,
        entregadas: 0,
        declinadas: 0,
        errores: 0,
        declinaciones_por_causa: {},
        latencia_media_ms: null,
        costo_usd: 0,
      }),
    )
    await flushPromises()

    const aviso = wrapper.get('[data-test="degradado"]')
    expect(aviso.text()).toContain('El seguimiento está desactivado')
    expect(wrapper.get('[data-test="costo"]').text()).toBe('USD 0.0000')
    expect(wrapper.get('[data-test="latencia"]').text()).toBe('sin datos')
    expect(wrapper.text()).toContain('Sin declinaciones en la ventana.')
  })

  it('informa el fallo de la petición sin romper la vista', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, json: async () => ({}) })))
    wrapper = mount(MetricsView)
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('No se pudieron leer las métricas')
  })
})
