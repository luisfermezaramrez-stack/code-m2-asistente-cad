import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import GlbViewer from '../src/GlbViewer.vue'

const estado = vi.hoisted(() => ({
  vistas: [] as Array<{ x: number; y: number; z: number; zoom: number }>,
  png: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  descargas: [] as Array<{ href: string; download: string }>,
  planos: [] as Array<{ normal: { x: number; y: number; z: number }; constant: number }>,
  materiales: [] as Array<{ clippingPlanes: unknown[]; needsUpdate: boolean; dispose(): void }>,
  caras: [] as Array<{
    visible: boolean
    posicion: { x: number; y: number; z: number }
    escala: { x: number; y: number; z: number }
    rotacion: { x: number; y: number; z: number }
    stencilFunc: number
  }>,
  mallasTapa: [] as Array<{ onAfterRender?: (renderer: unknown) => void }>,
  cargaModelos: 0,
  clipping: false,
  limpiezasStencil: 0,
}))

vi.mock('three', () => {
  class Vector3Mock {
    x: number; y: number; z: number
    constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z }
    set(x: number, y: number, z: number) { this.x = x; this.y = y; this.z = z; return this }
    copy(other: Vector3Mock) { return this.set(other.x, other.y, other.z) }
    sub(other: Vector3Mock) { this.x -= other.x; this.y -= other.y; this.z -= other.z; return this }
    length() { return Math.hypot(this.x, this.y, this.z) }
    setFromSpherical(s: { radius: number; theta: number; phi: number }) {
      const sin = Math.sin(s.phi) * s.radius
      return this.set(sin * Math.sin(s.theta), Math.cos(s.phi) * s.radius, sin * Math.cos(s.theta))
    }
  }
  class EulerMock {
    x = 0; y = 0; z = 0
    set(x: number, y: number, z: number) { this.x = x; this.y = y; this.z = z; return this }
  }
  class SphericalMock {
    radius = 1; theta = 0; phi = Math.PI / 2
    setFromVector3(v: Vector3Mock) {
      this.radius = v.length()
      if (this.radius !== 0) {
        this.theta = Math.atan2(v.x, v.z)
        this.phi = Math.acos(Math.min(1, Math.max(-1, v.y / this.radius)))
      }
      return this
    }
  }
  class Object3DMock {
    position = new Vector3Mock()
    rotation = new EulerMock()
    scale = new Vector3Mock(1, 1, 1)
    visible = true
    renderOrder = 0
    children: Object3DMock[] = []
    add(...objetos: Object3DMock[]) { this.children.push(...objetos) }
    traverse(callback: (obj: Object3DMock) => void) {
      callback(this)
      for (const hijo of this.children) hijo.traverse(callback)
    }
    dispose() {}
  }
  class PlaneGeometryMock { dispose() {} }
  class MeshBasicMaterialMock {
    color: unknown
    side = 0
    colorWrite = true
    depthWrite = true
    depthTest = true
    stencilWrite = false
    stencilRef = 0
    stencilFunc = 0
    stencilFail = 0
    stencilZFail = 0
    stencilZPass = 0
    clippingPlanes: unknown[] = []
    needsUpdate = false
    constructor(params: Record<string, unknown> = {}) { Object.assign(this, params) }
    dispose() {}
  }
  class MeshMock extends Object3DMock {
    onAfterRender?: (renderer: unknown) => void
    constructor(public geometry: PlaneGeometryMock | { dispose(): void }, public material: MeshBasicMaterialMock) {
      super()
      if (geometry instanceof PlaneGeometryMock) {
        const malla = this
        estado.mallasTapa.push(this)
        estado.caras.push({
          get visible() { return malla.visible },
          get posicion() { return { x: malla.position.x, y: malla.position.y, z: malla.position.z } },
          get escala() { return { x: malla.scale.x, y: malla.scale.y, z: malla.scale.z } },
          get rotacion() { return { x: malla.rotation.x, y: malla.rotation.y, z: malla.rotation.z } },
          get stencilFunc() { return malla.material.stencilFunc },
        })
      }
    }
  }
  class GroupMock extends Object3DMock {}
  class PlaneMock {
    normal = new Vector3Mock(0, 0, 1)
    constant = 0
    constructor(normal = new Vector3Mock(0, 0, 1), constant = 0) {
      this.normal.copy(normal)
      this.constant = constant
      estado.planos.push(this)
    }
  }
  class Box3Mock {
    setFromObject(_obj: Object3DMock) { return this }
    getCenter(target: Vector3Mock) { return target.set(0, 0, 0) }
    getSize(target: Vector3Mock) { return target.set(40, 30, 5) }
  }
  class OrthographicCameraMock {
    left = -1; right = 1; top = 1; bottom = -1; zoom = 1
    position = new Vector3Mock()
    updateProjectionMatrix() {}
  }
  class WebGLRendererMock {
    domElement: HTMLCanvasElement
    toneMapping = 0
    toneMappingExposure = 1
    constructor() {
      this.domElement = document.createElement('canvas')
      this.domElement.toDataURL = () => estado.png
      estado.clipping = false
    }
    get localClippingEnabled() { return estado.clipping }
    set localClippingEnabled(value: boolean) { estado.clipping = value }
    setPixelRatio(_value: number) {}
    setSize(_width: number, _height: number, _updateStyle?: boolean) {}
    render(_scene: unknown, camera: OrthographicCameraMock) {
      estado.vistas.push({ x: camera.position.x, y: camera.position.y, z: camera.position.z, zoom: camera.zoom })
      for (const malla of estado.mallasTapa) malla.onAfterRender?.(this)
    }
    clearStencil() { estado.limpiezasStencil++ }
    dispose() {}
  }
  return {
    ACESFilmicToneMapping: 1,
    AlwaysStencilFunc: 519,
    BackSide: 1,
    Box3: Box3Mock,
    Color: class { constructor(public value: string) {} },
    DecrementWrapStencilOp: 34056,
    DirectionalLight: class { position = new Vector3Mock(); dispose() {} },
    DoubleSide: 2,
    FrontSide: 0,
    Group: GroupMock,
    HemisphereLight: class { dispose() {} },
    IncrementWrapStencilOp: 34055,
    LoadingManager: class { setURLModifier(_fn: (url: string) => string) {} },
    Mesh: MeshMock,
    MeshBasicMaterial: MeshBasicMaterialMock,
    NotEqualStencilFunc: 517,
    OrthographicCamera: OrthographicCameraMock,
    Plane: PlaneMock,
    PlaneGeometry: PlaneGeometryMock,
    PMREMGenerator: class {
      constructor(_renderer: WebGLRendererMock) {}
      fromScene(_scene: unknown) { return { texture: {} } }
      dispose() {}
    },
    ReplaceStencilOp: 34054,
    Scene: class {
      background: unknown
      environment: unknown
      add(_obj: unknown) {}
    },
    Spherical: SphericalMock,
    Vector3: Vector3Mock,
    WebGLRenderer: WebGLRendererMock,
  }
})

vi.mock('three/addons/loaders/GLTFLoader.js', () => ({
  GLTFLoader: class {
    constructor(_manager: unknown) {}
    async parseAsync(_data: ArrayBuffer, _path: string) {
      estado.cargaModelos++
      const material = { clippingPlanes: [] as unknown[], needsUpdate: false, dispose() {} }
      estado.materiales.push(material)
      const scene = {
        position: { sub() {} },
        geometry: { dispose() {} },
        material,
        children: [] as unknown[],
        visible: true,
        renderOrder: 0,
        traverse(callback: (obj: unknown) => void) { callback(this) },
        dispose() {},
      }
      return { scene }
    }
  },
}))

vi.mock('three/addons/controls/OrbitControls.js', () => ({
  OrbitControls: class {
    target = { set() {} }
    addEventListener(_event: string, _callback: () => void) {}
    update() {}
    dispose() {}
  },
}))

vi.mock('three/addons/environments/RoomEnvironment.js', () => ({
  RoomEnvironment: class { dispose() {} },
}))

function boton(wrapper: VueWrapper, texto: string) {
  const encontrado = wrapper.findAll('button').find((item) => item.text() === texto)
  if (!encontrado) throw new Error(`Falta el botón ${texto}`)
  return encontrado
}

function botonQueContenga(wrapper: VueWrapper, texto: string) {
  const encontrado = wrapper.findAll('button').find((item) => item.text().includes(texto))
  if (!encontrado) throw new Error(`Falta el botón que contenga ${texto}`)
  return encontrado
}

function ultimaVista() {
  const vista = estado.vistas.at(-1)
  if (!vista) throw new Error('No se registró ninguna renderización')
  return vista
}

function ultimoPlano() {
  const plano = estado.planos.at(-1)
  if (!plano) throw new Error('No se creó ningún plano de corte')
  return plano
}

function ultimaCara() {
  const cara = estado.caras.at(-1)
  if (!cara) throw new Error('No se creó ninguna cara de sección')
  return cara
}

async function montar(cajaMm?: string) {
  estado.vistas.length = 0
  estado.descargas.length = 0
  estado.planos.length = 0
  estado.materiales.length = 0
  estado.caras.length = 0
  estado.mallasTapa.length = 0
  estado.cargaModelos = 0
  estado.limpiezasStencil = 0
  estado.png = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, arrayBuffer: async () => new ArrayBuffer(8) })))
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} })
  const wrapper = mount(GlbViewer, { props: { url: 'blob:modelo', token: 'token-de-prueba', cajaMm } })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('GlbViewer · HU-39', () => {
  beforeEach(() => {
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      estado.descargas.push({ href: this.href, download: this.download })
    })
  })

  it('AC1: reproduce exactamente cada vista ortogonal al volver a seleccionarla', async () => {
    const wrapper = await montar('40.00x30.00x5.00')

    for (const etiqueta of ['Frontal', 'Superior', 'Lateral']) {
      await boton(wrapper, etiqueta).trigger('click')
      const primera = ultimaVista()
      await boton(wrapper, etiqueta).trigger('click')

      expect(ultimaVista()).toEqual(primera)
      expect(boton(wrapper, etiqueta).attributes('aria-pressed')).toBe('true')
    }
  })

  it('AC2: descarga la vista actual como PNG y avisa si el lienzo está vacío', async () => {
    const wrapper = await montar('40.00x30.00x5.00')

    await boton(wrapper, 'Capturar PNG').trigger('click')

    expect(estado.descargas).toHaveLength(1)
    expect(estado.descargas[0]?.href).toMatch(/^data:image\/png;base64,/)
    expect(estado.descargas[0]?.download).toBe('vista-frontal-mm.png')

    estado.png = 'data:image/png;base64,'
    await boton(wrapper, 'Capturar PNG').trigger('click')

    expect(wrapper.find('[role="alert"]').text()).toContain('No se pudo capturar la vista')
    expect(estado.descargas).toHaveLength(1)
  })

  it('AC3: muestra las cotas generales tomadas de caja_mm', async () => {
    const wrapper = await montar('40.00x30.00x5.00')

    const texto = wrapper.text()

    expect(texto).toContain('40.00 mm')
    expect(texto).toContain('30.00 mm')
    expect(texto).toContain('5.00 mm')
    expect(wrapper.find('dl').attributes('aria-label')).toBe('Cotas generales de la pieza')
  })

  it('AC4: cambia las cotas y el nombre del PNG a pulgadas', async () => {
    const wrapper = await montar('40.00x30.00x5.00')

    await wrapper.find<HTMLSelectElement>('#unidad-medidas').setValue('in')

    expect(wrapper.text()).toContain('1.57 in')
    expect(wrapper.text()).toContain('1.18 in')
    expect(wrapper.text()).toContain('0.20 in')

    await boton(wrapper, 'Capturar PNG').trigger('click')

    expect(estado.descargas[0]?.download).toBe('vista-frontal-in.png')
  })
})

describe('GlbViewer · HU-50', () => {
  it('AC1: corta por el eje Z con sección cerrada y stitch de stencil', async () => {
    const wrapper = await montar('40.00x30.00x5.00')

    await botonQueContenga(wrapper, 'Cortar Z (alto)').trigger('click')

    expect(ultimoPlano().normal).toMatchObject({ x: 0, y: 0, z: 1 })
    expect(ultimoPlano().constant).toBe(0)
    expect(estado.clipping).toBe(true)
    expect(estado.materiales[0]?.clippingPlanes).toHaveLength(1)
    expect(ultimaCara().visible).toBe(true)
    expect(ultimaCara().stencilFunc).toBe(517)
    expect(estado.limpiezasStencil).toBeGreaterThan(0)
  })

  it('AC2: ajusta, invierte y desactiva el corte sin recargar el modelo', async () => {
    const wrapper = await montar('40.00x30.00x5.00')
    await botonQueContenga(wrapper, 'Cortar Z (alto)').trigger('click')

    await wrapper.find<HTMLInputElement>('#posicion-corte').setValue('4')

    expect(ultimoPlano().constant).toBeCloseTo(-1.5)
    expect(vi.mocked(globalThis.fetch)).toHaveBeenCalledTimes(1)

    await boton(wrapper, 'Invertir corte').trigger('click')

    expect(ultimoPlano().normal.z).toBe(-1)
    expect(ultimoPlano().constant).toBeCloseTo(1.5)

    await boton(wrapper, 'Desactivar corte').trigger('click')

    expect(estado.materiales[0]?.clippingPlanes).toHaveLength(0)
    expect(ultimaCara().visible).toBe(false)
  })

  it('AC3: expone controles etiquetados, estado en vivo y atajos de teclado', async () => {
    const wrapper = await montar('40.00x30.00x5.00')

    expect(wrapper.find('[aria-label="Cortes y secciones"]').exists()).toBe(true)
    expect(wrapper.find('#posicion-corte').attributes('disabled')).toBeDefined()
    expect(wrapper.find('[role="status"][aria-live="polite"]').text()).toContain('Corte desactivado')

    const lienzo = wrapper.find('.model-canvas')
    await lienzo.trigger('keydown', { key: '6' })

    expect(botonQueContenga(wrapper, 'Cortar Z (alto)').attributes('aria-pressed')).toBe('true')
    expect(wrapper.find('[role="status"][aria-live="polite"]').text()).toContain('2.50 mm')

    await lienzo.trigger('keydown', { key: 'c' })

    expect(boton(wrapper, 'Activar corte').attributes('aria-pressed')).toBe('false')

    await lienzo.trigger('keydown', { key: '4' })
    await lienzo.trigger('keydown', { key: ']' })

    expect(wrapper.find('#posicion-corte').attributes('aria-valuetext')).toBe('20.40 mm')
  })
})
