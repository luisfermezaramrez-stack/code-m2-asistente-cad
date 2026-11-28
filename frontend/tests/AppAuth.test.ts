import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import App from '../src/App.vue'
import { createAppRouter } from '../src/router'
import { FakeCadService } from './fakeCadService'

describe('acceso HU-53 en la SPA', () => {
  let service: FakeCadService
  let wrapper: VueWrapper

  async function montar() {
    const router = createAppRouter(createMemoryHistory())
    await router.push('/nueva-solicitud')
    await router.isReady()
    wrapper = mount(App, {
      attachTo: document.body,
      global: {
        plugins: [router],
        stubs: { GlbViewer: { props: ['url'], template: '<div data-testid="visor-simulado" />' } },
      },
    })
    await flushPromises()
  }

  beforeEach(async () => {
    service = new FakeCadService()
    service.sesion = { requerido: true, autenticado: false, usuario: null }
    vi.stubGlobal('fetch', service.fetch)
    await montar()
  })

  afterEach(() => {
    wrapper.unmount()
    document.body.innerHTML = ''
    window.localStorage.clear()
    vi.unstubAllGlobals()
  })

  async function entrar(usuario = 'ana', clave = 'clave-ana') {
    await wrapper.get('#usuario').setValue(usuario)
    await wrapper.get('#clave').setValue(clave)
    await wrapper.get('.acceso-form').trigger('submit')
    await flushPromises()
  }

  const generarBoton = () => wrapper.findAll('button').find((b) => b.text() === 'Generar pieza')

  it('muestra sólo la pantalla de acceso antes de iniciar sesión', () => {
    expect(wrapper.find('.acceso-form').exists()).toBe(true)
    expect(wrapper.text()).toContain('Iniciar sesión')
    expect(wrapper.find('nav').exists()).toBe(false)
    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Diseño preliminar')
    expect(wrapper.find('button.theme-toggle').exists()).toBe(true)
  })

  it('entra al shell tras autenticarse', async () => {
    await entrar()

    expect(wrapper.find('.acceso-form').exists()).toBe(false)
    expect(wrapper.text()).toContain('Generando como ana')
    expect(wrapper.findAll('nav a')).toHaveLength(3)
    expect(wrapper.find('textarea#descripcion').exists()).toBe(true)
    expect(generarBoton()?.attributes('disabled')).toBeUndefined()
  })

  it('muestra el error público de credenciales inválidas dentro del acceso', async () => {
    service.fetch = vi.fn(async () => new Response('', { status: 401 }))
    vi.stubGlobal('fetch', service.fetch)

    await entrar('ana', 'mala')

    expect(wrapper.get('.acceso [role="alert"]').text()).toContain('Usuario o clave incorrectos.')
    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.find('nav').exists()).toBe(false)
  })

  it('informa un cierre de sesión fallido y conserva la sesión', async () => {
    await entrar()
    const original = service.fetch.getMockImplementation()!
    service.fetch.mockImplementation((url, init) => String(url) === '/v1/auth/logout'
      ? Promise.reject(new Error('sin red')) : original(url, init))

    await wrapper.findAll('button').find((b) => b.text() === 'Cerrar sesión')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('No se pudo cerrar la sesión. Vuelve a intentarlo.')
    expect(wrapper.text()).toContain('Generando como ana')
    expect(wrapper.find('textarea#descripcion').exists()).toBe(true)
  })

  it('vuelve a la pantalla de acceso al cerrar sesión', async () => {
    await entrar()

    await wrapper.findAll('button').find((b) => b.text() === 'Cerrar sesión')!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.acceso-form').exists()).toBe(true)
    expect(wrapper.find('nav').exists()).toBe(false)
  })

  it('abre el shell sin acceso cuando el servicio no exige sesión', async () => {
    service.sesion = { requerido: false, autenticado: false, usuario: null }
    wrapper.unmount()
    await montar()

    expect(wrapper.find('.acceso-form').exists()).toBe(false)
    expect(wrapper.find('textarea#descripcion').exists()).toBe(true)
  })
})
