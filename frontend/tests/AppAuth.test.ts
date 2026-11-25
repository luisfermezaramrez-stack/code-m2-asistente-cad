import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../src/App.vue'
import { FakeCadService } from './fakeCadService'

describe('acceso HU-53 en la SPA', () => {
  let service: FakeCadService
  let wrapper: VueWrapper

  beforeEach(async () => {
    service = new FakeCadService()
    service.sesion = { requerido: true, autenticado: false, usuario: null }
    vi.stubGlobal('fetch', service.fetch)
    wrapper = mount(App, {
      attachTo: document.body,
      global: {
        stubs: { GlbViewer: { props: ['url'], template: '<div data-testid="visor-simulado" />' } },
      },
    })
    await flushPromises()
  })

  afterEach(() => {
    wrapper.unmount()
    vi.unstubAllGlobals()
  })

  const generarBoton = () => wrapper.findAll('button').find((b) => b.text() === 'Generar pieza')!

  it('bloquea la generación hasta iniciar sesión', async () => {
    expect(wrapper.text()).toContain('Iniciar sesión')
    expect(generarBoton().attributes('disabled')).toBeDefined()

    await wrapper.get('#usuario').setValue('ana')
    await wrapper.get('#clave').setValue('clave-ana')
    await wrapper.get('.sesion-form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Generando como ana')
    expect(generarBoton().attributes('disabled')).toBeUndefined()
  })

  it('muestra el error público de credenciales inválidas', async () => {
    service.fetch = vi.fn(async () => new Response('', { status: 401 }))
    vi.stubGlobal('fetch', service.fetch)
    await wrapper.get('#usuario').setValue('ana')
    await wrapper.get('#clave').setValue('mala')
    await wrapper.get('.sesion-form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Usuario o clave incorrectos.')
    expect(generarBoton().attributes('disabled')).toBeDefined()
  })
})
