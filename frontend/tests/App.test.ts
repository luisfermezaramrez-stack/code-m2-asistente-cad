import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../src/App.vue'
import { FakeCadService, event } from './fakeCadService'

let service: FakeCadService
let wrapper: VueWrapper
const result = { step: 'outputs/job/pieza.step', glb: 'outputs/job/pieza.glb', bom_csv: 'outputs/job/materiales.csv' }

async function start(text = 'Espaciador de 14 mm') {
  await wrapper.get('textarea').setValue(text)
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}
async function sendStages() {
  service.send(event('validando', 1), true)
  service.send(event('generando', 2), true)
  await flushPromises()
}
function button(text: string) { return wrapper.findAll('button').find((item) => item.text() === text)! }

beforeEach(() => {
  service = new FakeCadService()
  vi.stubGlobal('fetch', service.fetch)
  wrapper = mount(App, {
    attachTo: document.body,
    // Solo el renderer WebGL está sustituido; el flujo Vue y el parser SSE son reales.
    global: { stubs: { GlbViewer: { props: ['url'], template: '<div data-testid="visor-simulado">Visor WebGL simulado: {{ url }}</div>' } } },
  })
})
afterEach(() => { wrapper.unmount(); document.body.innerHTML = ''; vi.unstubAllGlobals(); vi.useRealTimers() })

describe('SPA conectada a FastAPI simulado', () => {
  it('muestra aviso profesional y estado vacío sin muestras técnicas', () => {
    expect(wrapper.text()).toContain('Diseño preliminar: requiere revisión profesional')
    expect(wrapper.text()).toContain('Sin solicitud')
    expect(wrapper.findAll('a[download]')).toHaveLength(0)
    expect(wrapper.text()).not.toMatch(/MAQUETA|SSE|localhost|simulado/)
  })

  it.each(['', '   ', 'x'.repeat(1001)])('valida entrada y enfoca el campo sin llamar a servicios', async (text) => {
    await start(text)
    expect(service.fetch).not.toHaveBeenCalled()
    expect(wrapper.get('[role="alert"]').text()).toContain('entre 1 y 1000')
    expect(document.activeElement).toBe(wrapper.get('textarea').element)
  })

  it('envía POST y AbortSignal, sin inventar etapas antes de los eventos', async () => {
    await start()
    expect(service.fetch).toHaveBeenCalledWith('/generar', expect.objectContaining({
      method: 'POST', headers: { Accept: 'text/event-stream', 'Content-Type': 'application/json' },
      signal: expect.any(AbortSignal),
    }))
    expect(service.posts[0]?.body).toEqual({ texto: 'Espaciador de 14 mm' })
    expect(wrapper.text()).toContain('El servicio aún no informa progreso')
    expect(wrapper.findAll('.steps li')).toHaveLength(0)
    service.send(event('validando', 1), true)
    await flushPromises()
    expect(wrapper.findAll('.steps li').map((item) => item.text())).toEqual(['Validando solicitud'])
    expect(wrapper.text()).not.toContain('Generando pieza')
  })

  it('procesa frames fragmentados y ofrece solo enlaces propios, nunca rutas del resultado', async () => {
    await start(); await sendStages()
    service.send(event('verificado', 3, { resultado: result }), true)
    await flushPromises()
    expect(wrapper.findAll('.steps li').map((item) => item.text())).toEqual(['Validando solicitud', 'Generando pieza', 'Pieza verificada'])
    expect(wrapper.findAll('a[download]').map((item) => item.attributes('href'))).toEqual([
      '/generaciones/job1/archivos/step', '/generaciones/job1/archivos/glb', '/generaciones/job1/archivos/csv',
    ])
    expect(wrapper.find('[data-testid="visor-simulado"]').exists()).toBe(true)
    expect(wrapper.html()).not.toContain('outputs/')
  })

  it('STEP y CSV permanecen disponibles sin GLB', async () => {
    service.files.delete('glb')
    await start(); await sendStages()
    service.send(event('verificado', 3, { resultado: result }))
    await flushPromises()
    expect(wrapper.findAll('a[download]')).toHaveLength(2)
    expect(wrapper.get('a[download="pieza.step"]').attributes('href')).toBe('/generaciones/job1/archivos/step')
    expect(wrapper.text()).toContain('Vista 3D no disponible')
    expect(wrapper.find('[data-testid="visor-simulado"]').exists()).toBe(false)
  })

  it('GLB no depende del STEP y no ofrece archivos inexistentes', async () => {
    service.files = new Set(['glb'])
    await start(); await sendStages()
    service.send(event('verificado', 3, { resultado: result }))
    await flushPromises()
    expect(wrapper.findAll('a[download]')).toHaveLength(1)
    expect(wrapper.text()).toContain('No hay archivo STEP disponible')
    expect(wrapper.find('[data-testid="visor-simulado"]').exists()).toBe(true)
  })

  it.each(['csv', 'bom_csv'])('conserva lista de materiales con clave %s del pipeline', async (key) => {
    await start(); await sendStages()
    service.send(event('verificado', 3, { resultado: { step: result.step, [key]: 'materiales.csv' } }))
    await flushPromises()
    expect(wrapper.get('a[download="pieza.csv"]').attributes('href')).toBe('/generaciones/job1/archivos/csv')
  })

  it('comunica el detalle público de un error HTTP sin ofrecer archivos', async () => {
    service.postStatus = 503
    service.postDetail = 'El servicio de generación no está disponible.'
    await start()
    expect(wrapper.text()).toContain('El servicio de generación no está disponible.')
    expect(wrapper.findAll('a[download]')).toHaveLength(0)
  })

  it('limpia visor y descargas al empezar de nuevo y conserva la descripción al declinar', async () => {
    await start(); await sendStages()
    service.send(event('verificado', 3, { resultado: result }))
    await flushPromises()
    await start('Turbina fuera de catálogo')
    expect(wrapper.findAll('a[download]')).toHaveLength(0)
    expect(wrapper.find('[data-testid="visor-simulado"]').exists()).toBe(false)
    service.send(event('validando', 1))
    service.send(event('declinado', 2, { motivo: 'Fuera del catálogo admitido' }))
    await flushPromises()
    expect(wrapper.text()).toContain('Solicitud declinada')
    expect(wrapper.text()).toContain('Fuera del catálogo admitido')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('Turbina fuera de catálogo')
    expect(wrapper.findAll('a[download]')).toHaveLength(0)
  })

  it('distingue DELETE 202 de cancelación local confirmada y no aborta antes de confirmarla', async () => {
    await start(); await sendStages()
    await button('Cancelar solicitud').trigger('click'); await flushPromises()
    expect(service.fetch).toHaveBeenCalledWith('/generaciones/job1', expect.objectContaining({ method: 'DELETE' }))
    expect(wrapper.text()).toContain('Cancelación solicitada')
    expect(wrapper.text()).not.toContain('Procesamiento local detenido')
    expect(service.posts[0]?.signal.aborted).toBe(false)
    service.send(event('cancelado', 3, { cancelacion_solicitada: true, pipeline_detenido: true, cancelacion_remota_confirmada: false }))
    await flushPromises()
    expect(wrapper.text()).toContain('Procesamiento local detenido')
    expect(wrapper.text()).toContain('No se confirma la detención de servicios remotos')
  })

  it('respeta éxito terminal si gana la carrera contra cancelar', async () => {
    await start(); await sendStages()
    service.deleteResult = event('verificado', 3, { resultado: result })
    await button('Cancelar solicitud').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('Pieza verificada')
    expect(wrapper.text()).not.toContain('Procesamiento local detenido')
    expect(wrapper.findAll('a[download]')).toHaveLength(3)
    service.close(); await flushPromises()
  })

  it('abortar la espera no confirma detención; GET recupera un terminal real', async () => {
    await start(); await sendStages()
    await button('Interrumpir espera').trigger('click'); await flushPromises()
    expect(service.posts[0]?.signal.aborted).toBe(true)
    expect(wrapper.text()).toContain('No se ha confirmado que el procesamiento se detuviera')
    expect(wrapper.text()).toContain('La desconexión solicita cancelación local')
    expect(wrapper.text()).toContain('falta confirmar su recepción y detención')
    expect(wrapper.text()).not.toContain('Procesamiento local detenido')
    service.current = event('generando', 2, { cancelacion_solicitada: true })
    await button('Actualizar estado').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('Cancelación solicitada')
    expect(wrapper.text()).not.toContain('Procesamiento local detenido')
    service.current = event('cancelado', 3, { cancelacion_solicitada: true, pipeline_detenido: true })
    await button('Actualizar estado').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('Procesamiento local detenido')
  })

  it('EOF sin terminal se declara como desconexión y consulta por ID', async () => {
    await start(); await sendStages(); service.close(); await flushPromises()
    expect(wrapper.text()).toContain('Se interrumpió la conexión antes del resultado')
    expect(wrapper.text()).toContain('La desconexión solicita cancelación local')
    expect(wrapper.text()).not.toContain('podría continuar en el servidor')
    expect(service.fetch).toHaveBeenCalledWith('/generaciones/job1', expect.objectContaining({ method: 'GET' }))
    expect(wrapper.text()).not.toContain('Pieza verificada')
  })

  it('timeout configurable interrumpe una espera real sin añadir etapas', async () => {
    vi.useFakeTimers()
    await wrapper.get('#timeout').setValue('5')
    await start()
    await vi.advanceTimersByTimeAsync(5000); await flushPromises()
    expect(service.posts[0]?.signal.aborted).toBe(true)
    expect(wrapper.text()).toContain('Se agotó el tiempo de espera')
    expect(wrapper.text()).toContain('La desconexión solicita cancelación local')
    expect(wrapper.text()).not.toContain('podría continuar en el servidor')
    expect(wrapper.text()).not.toContain('Procesamiento local detenido')
    expect(wrapper.findAll('.steps li')).toHaveLength(0)
  })

  it.each([422, 503])('maneja error HTTP %s sin fingir un terminal del pipeline', async (status) => {
    service.postStatus = status
    service.postDetail = [{ loc: ['body', 'texto'] }]
    await start()
    expect(wrapper.text()).toContain(status === 422 ? 'Solicitud inválida' : 'El servicio no está disponible')
    expect(wrapper.findAll('.steps li')).toHaveLength(0)
  })

  it('muestra error terminal pero no direcciones del modelo ni trazas', async () => {
    await start(); await sendStages()
    service.send(event('error', 3, { motivo: 'Fallo en http://10.0.0.5:8080 con api_key=secreto', codigo_http: 503 }))
    await flushPromises()
    expect(wrapper.text()).toContain('No se pudo completar')
    expect(wrapper.text()).not.toMatch(/10\.0\.0\.5|secreto|api_key/)
    expect(wrapper.findAll('a[download]')).toHaveLength(0)
  })

  it('un corte de red solicita cancelación local sin afirmar recepción ni detención', async () => {
    await start(); await sendStages()
    service.posts[0]!.controller.error(new TypeError('Failed to fetch'))
    await flushPromises()
    expect(wrapper.text()).toContain('La desconexión solicita cancelación local')
    expect(wrapper.text()).toContain('falta confirmar su recepción y detención')
    expect(wrapper.text()).toContain('No se confirma la detención de servicios remotos')
    expect(wrapper.text()).not.toContain('Procesamiento local detenido')
    expect(service.fetch).toHaveBeenCalledWith('/generaciones/job1', expect.objectContaining({ method: 'GET' }))
  })

  it('muestra la configuración ausente en un error terminal SSE sin ofrecer descargas', async () => {
    await start()
    service.send(event('validando', 1))
    service.send(event('error', 2, { motivo: 'El modelo no está configurado: falta DEEPSEEK_API_KEY.', codigo_http: 503 }))
    await flushPromises()
    expect(wrapper.text()).toContain('El modelo no está configurado: falta DEEPSEEK_API_KEY.')
    expect(wrapper.findAll('a[download]')).toHaveLength(0)
  })

  it('muestra el mismo diagnóstico seguro si llega como error HTTP', async () => {
    service.postStatus = 503
    service.postDetail = 'El modelo no está configurado: falta DEEPSEEK_API_KEY.'
    await start()
    expect(wrapper.text()).toContain('El modelo no está configurado: falta DEEPSEEK_API_KEY.')
    expect(wrapper.text()).not.toContain('La desconexión solicita cancelación local')
  })

  it('declara falta de progreso si el servicio no devuelve SSE', async () => {
    service.fetch.mockResolvedValue(Response.json({ resultado: 'generada' }))
    await start()
    expect(wrapper.text()).toContain('El servicio no informa progreso')
    expect(wrapper.findAll('.steps li')).toHaveLength(0)
  })

  it('explica un fallo de conexión sin identificarlo como error del pipeline', async () => {
    service.fetch.mockRejectedValue(new Error('No hay conexión con el servicio.'))
    await start()
    expect(wrapper.text()).toContain('No hay conexión con el servicio')
    expect(wrapper.findAll('.steps li')).toHaveLength(0)
  })

  it('no inventa confirmación si DELETE falla y conserva la opción de reintentar', async () => {
    await start(); await sendStages()
    const original = service.fetch.getMockImplementation()!
    service.fetch.mockImplementation((url, init) => init?.method === 'DELETE'
      ? Promise.resolve(Response.json({ detail: 'error' }, { status: 503 })) : original(url, init))
    await button('Cancelar solicitud').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('No se pudo confirmar la solicitud de cancelación')
    expect(button('Cancelar solicitud').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).not.toContain('Procesamiento local detenido')
  })

  it('GET 404 no se convierte en confirmación de cancelación', async () => {
    await start(); await sendStages()
    service.getStatus = 404
    await button('Interrumpir espera').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('No se puede confirmar su estado')
    expect(wrapper.text()).not.toContain('Procesamiento local detenido')
  })

  it('un fallo HEAD en GLB no bloquea las otras descargas', async () => {
    const original = service.fetch.getMockImplementation()!
    service.fetch.mockImplementation((url, init) => String(url).endsWith('/glb')
      ? Promise.reject(new TypeError('Red no disponible')) : original(url, init))
    await start(); await sendStages()
    service.send(event('verificado', 3, { resultado: result })); await flushPromises()
    expect(wrapper.findAll('a[download]')).toHaveLength(2)
    expect(wrapper.get('a[download="pieza.csv"]').attributes('href')).toContain('/archivos/csv')
  })

  it('desmontar aborta la espera sin anunciar cancelación completa', async () => {
    await start()
    wrapper.unmount()
    expect(service.posts[0]?.signal.aborted).toBe(true)
  })

  it('trata el motivo de declinación como texto, no como HTML', async () => {
    await start()
    service.send(event('validando', 1))
    service.send(event('declinado', 2, { motivo: '<img src=x onerror=alert(1)>' }))
    await flushPromises()
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('<img src=x onerror=alert(1)>')
  })

  it('rechaza un terminal cancelado sin confirmación del pipeline', async () => {
    await start(); await sendStages()
    service.current = event('generando', 2)
    const malformed = event('cancelado', 3)
    service.send(malformed)
    // GET devuelve el estado activo anterior, no la confirmación inválida.
    service.current = event('generando', 2)
    await flushPromises()
    expect(wrapper.text()).not.toContain('Procesamiento local detenido')
    expect(wrapper.text()).toContain('Respuesta inválida')
  })

  it('rechaza eventos fuera de orden', async () => {
    await start()
    service.send(event('generando', 1))
    await flushPromises()
    expect(wrapper.text()).toContain('progreso inválido')
    // El snapshot GET es información recibida; no se inventa la validación faltante.
    expect(wrapper.findAll('.steps li').map((item) => item.text())).toEqual(['Generando pieza'])
  })

  it('no atribuye la respuesta de una consulta antigua a una solicitud nueva', async () => {
    await start(); await sendStages()
    await button('Interrumpir espera').trigger('click'); await flushPromises()
    let resolve!: (response: Response) => void
    const original = service.fetch.getMockImplementation()!
    service.fetch.mockImplementation((url, init) => String(url) === '/generaciones/job1' && init?.method === 'GET'
      ? new Promise((done) => { resolve = done }) : original(url, init))
    await button('Actualizar estado').trigger('click')
    // El doble ignora abort deliberadamente para reproducir una respuesta tardía.
    await start('Otra placa')
    resolve(Response.json(event('verificado', 3, { resultado: result }))); await flushPromises()
    expect(wrapper.findAll('a[download]')).toHaveLength(0)
  })
})
