import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, type Router } from 'vue-router'
import App from '../src/App.vue'
import { THEME_STORAGE_KEY } from '../src/design/theme'
import { createAppRouter } from '../src/router'
import { FakeCadService, event } from './fakeCadService'

describe('AC1 y AC2 · URL propia y estado recuperable', () => {
  let router: Router
  let wrapper: VueWrapper

  beforeEach(async () => {
    const service = new FakeCadService()
    vi.stubGlobal('fetch', service.fetch)
    router = createAppRouter(createMemoryHistory())
    await router.push('/')
    await router.isReady()
    wrapper = mount(App, { attachTo: document.body, global: { plugins: [router] } })
    await flushPromises()
  })

  afterEach(() => {
    wrapper.unmount()
    document.body.innerHTML = ''
    window.localStorage.clear()
    vi.unstubAllGlobals()
  })

  function enlace(texto: string) {
    return wrapper.findAll('nav a').find((item) => item.text() === texto)!
  }

  async function abrirEnOtraPestana(ruta: string) {
    wrapper.unmount()
    router = createAppRouter(createMemoryHistory())
    await router.push(ruta)
    await router.isReady()
    wrapper = mount(App, { attachTo: document.body, global: { plugins: [router] } })
    await flushPromises()
  }

  it('abre nueva solicitud en su propia URL con el formulario de generación', () => {
    expect(router.currentRoute.value.path).toBe('/nueva-solicitud')
    expect(enlace('Nueva solicitud').attributes('href')).toBe('/nueva-solicitud')
    expect(wrapper.find('textarea#descripcion').exists()).toBe(true)
    expect(wrapper.text()).toContain('Describe tu pieza')
  })

  it('cambia la URL y la vista al recorrer las tres entradas de navegación', async () => {
    await enlace('Historial').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/historial')
    expect(wrapper.text()).toContain('No hay solicitudes registradas para mostrar')
    expect(wrapper.find('textarea').exists()).toBe(false)

    await enlace('Ajustes').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/ajustes')
    expect(wrapper.text()).toContain('El tema se cambia desde la cabecera')
    expect(wrapper.find('textarea').exists()).toBe(false)

    await enlace('Nueva solicitud').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/nueva-solicitud')
    expect(wrapper.find('textarea#descripcion').exists()).toBe(true)
  })

  it('recupera borrador y tema al abrir /nueva-solicitud en otra pestaña', async () => {
    await wrapper.get('#descripcion').setValue('Espaciador persistido')
    await wrapper.get('#timeout').setValue('42')
    window.localStorage.setItem(THEME_STORAGE_KEY, 'dark')
    await flushPromises()

    await abrirEnOtraPestana('/nueva-solicitud')

    expect(router.currentRoute.value.path).toBe('/nueva-solicitud')
    expect((wrapper.get('#descripcion').element as HTMLTextAreaElement).value).toBe('Espaciador persistido')
    expect((wrapper.get('#timeout').element as HTMLInputElement).value).toBe('42')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('recupera la vista de historial desde su URL en otra pestaña', async () => {
    await abrirEnOtraPestana('/historial')

    expect(router.currentRoute.value.path).toBe('/historial')
    expect(wrapper.text()).toContain('No hay solicitudes registradas para mostrar')
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('recupera la vista de ajustes y el tema guardado desde su URL en otra pestaña', async () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, 'dark')

    await abrirEnOtraPestana('/ajustes')

    expect(router.currentRoute.value.path).toBe('/ajustes')
    expect(wrapper.text()).toContain('El tema se cambia desde la cabecera')
    expect(wrapper.get('button.theme-toggle').text()).toBe('Usar tema claro')
  })
})

describe('AC3 · Estados nuevos del shell diferenciados', () => {
  let service: FakeCadService
  let router: Router
  let wrapper: VueWrapper

  beforeEach(async () => {
    service = new FakeCadService()
    vi.stubGlobal('fetch', service.fetch)
    router = createAppRouter(createMemoryHistory())
    await router.push('/')
    await router.isReady()
    wrapper = mount(App, { attachTo: document.body, global: { plugins: [router] } })
    await flushPromises()
  })

  afterEach(() => {
    wrapper.unmount()
    document.body.innerHTML = ''
    vi.unstubAllGlobals()
  })

  async function visitar(ruta: string) {
    await router.push(ruta)
    await flushPromises()
  }

  it('distingue vacío, cargando y error en historial y ajustes', async () => {
    let liberar: () => void = () => {}
    service.esperaRegistros = new Promise<void>((resolve) => { liberar = resolve })
    await visitar('/historial')

    let bloque = wrapper.get('.estado-vista')
    expect(bloque.classes()).toContain('estado-vista--cargando')
    expect(bloque.text()).toContain('Cargando el historial')
    expect(bloque.attributes('aria-busy')).toBe('true')

    liberar()
    await flushPromises()
    bloque = wrapper.get('.estado-vista')
    expect(bloque.classes()).toContain('estado-vista--vacio')
    expect(bloque.text()).toContain('No hay solicitudes registradas')
    expect(bloque.attributes('role')).toBe('status')
    expect(bloque.attributes('aria-busy')).toBe('false')

    await visitar('/nueva-solicitud')
    service.registrosStatus = 503
    await visitar('/historial')
    bloque = wrapper.get('.estado-vista')
    expect(bloque.classes()).toContain('estado-vista--error')
    expect(bloque.text()).toContain('No se pudo cargar el historial')
    expect(bloque.attributes('role')).toBe('alert')
    expect(bloque.attributes('aria-busy')).toBe('false')

    // Ajustes conserva los estados de la consulta hasta que tenga datos propios.
    const estadosAjustes = [
      ['vacio', 'No hay ajustes adicionales'],
      ['cargando', 'Cargando los ajustes'],
      ['error', 'No se pudieron cargar los ajustes'],
    ] as const

    for (const [estado, texto] of estadosAjustes) {
      await visitar(`/ajustes?estado=${estado}`)

      const ajustes = wrapper.get('.estado-vista')
      expect(ajustes.classes()).toContain(`estado-vista--${estado}`)
      expect(ajustes.text()).toContain(texto)
      expect(ajustes.attributes('role')).toBe(estado === 'error' ? 'alert' : 'status')
      expect(ajustes.attributes('aria-busy')).toBe(estado === 'cargando' ? 'true' : 'false')
    }
  })

  it('muestra una vista no encontrada distinta para una ruta desconocida', async () => {
    await visitar('/no-existe')

    expect(wrapper.text()).toContain('Vista no encontrada')
    expect(wrapper.text()).toContain('La ruta solicitada no corresponde')
    expect(wrapper.get('.sin-ruta').classes()).toContain('viewport')
    expect(wrapper.find('.estado-vista').exists()).toBe(false)
    expect(wrapper.find('textarea').exists()).toBe(false)
  })
})

describe('AC4 · Navegación sólo con teclado', () => {
  let router: Router
  let wrapper: VueWrapper

  beforeEach(async () => {
    const service = new FakeCadService()
    vi.stubGlobal('fetch', service.fetch)
    router = createAppRouter(createMemoryHistory())
    await router.push('/')
    await router.isReady()
    wrapper = mount(App, { attachTo: document.body, global: { plugins: [router] } })
    await flushPromises()
  })

  afterEach(() => {
    wrapper.unmount()
    document.body.innerHTML = ''
    vi.unstubAllGlobals()
  })

  it('alcanza las tres entradas con Tab y Shift+Tab desde el propio nav', async () => {
    const enlaces = wrapper.findAll('nav a')
    expect(enlaces).toHaveLength(3)

    const [primero, segundo, tercero] = enlaces.map(
      (enlace) => enlace.element as HTMLAnchorElement,
    ) as [HTMLAnchorElement, HTMLAnchorElement, HTMLAnchorElement]
    primero.focus()
    expect(document.activeElement).toBe(primero)

    await wrapper.get('nav').trigger('keydown', { key: 'Tab' })
    expect(document.activeElement).toBe(segundo)

    await wrapper.get('nav').trigger('keydown', { key: 'Tab' })
    expect(document.activeElement).toBe(tercero)

    await wrapper.get('nav').trigger('keydown', { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(segundo)
  })

  it('activa la entrada enfocada con Enter y mantiene el skip link enfocable', async () => {
    const skip = wrapper.get('a.skip')
    expect(skip.attributes('href')).toBe('#contenido')
    ;(skip.element as HTMLAnchorElement).focus()
    expect(document.activeElement).toBe(skip.element)

    const ajustes = wrapper.findAll('nav a')[2]!.element as HTMLAnchorElement
    ajustes.focus()
    await wrapper.get('nav').trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/ajustes')
    expect(wrapper.text()).toContain('Ajustes')
  })
})

describe('AC2 · La generación pertenece al shell, no a la vista', () => {
  let service: FakeCadService
  let router: Router
  let wrapper: VueWrapper

  beforeEach(async () => {
    service = new FakeCadService()
    vi.stubGlobal('fetch', service.fetch)
    router = createAppRouter(createMemoryHistory())
    await router.push('/nueva-solicitud')
    await router.isReady()
    wrapper = mount(App, { attachTo: document.body, global: { plugins: [router] } })
    await flushPromises()
  })

  afterEach(() => {
    wrapper.unmount()
    document.body.innerHTML = ''
    window.localStorage.clear()
    vi.unstubAllGlobals()
  })

  async function visitar(ruta: string) {
    await router.push(ruta)
    await flushPromises()
  }

  it('conserva la generación en curso al navegar a historial y volver a nueva solicitud', async () => {
    // Arrange: una generación en curso con su stream SSE abierto.
    await wrapper.get('textarea').setValue('Espaciador de 14 mm')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    service.send(event('validando', 1))
    service.send(event('generando', 2))
    await flushPromises()
    expect(wrapper.get('.state strong').text()).toBe('Generando pieza')

    // Act: abandonar la vista de generación y regresar a ella.
    await visitar('/historial')
    await visitar('/nueva-solicitud')

    // Assert: navegar no aborta el stream ni pierde el trabajo en curso.
    expect(service.posts[0]?.signal.aborted).toBe(false)
    expect(wrapper.get('.state strong').text()).toBe('Generando pieza')
  })
})
