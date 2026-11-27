import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import GlbViewer from '../src/GlbViewer.vue'

const estado = vi.hoisted(() => ({
  vistas: [] as Array<{ x: number; y: number; z: number; zoom: number }>,
  png: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  descargas: [] as Array<{ href: string; download: string }>,
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
    traverse(callback: (obj: Object3DMock) => void) { callback(this) }
    dispose() {}
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
    }
    setPixelRatio(_value: number) {}
    setSize(_width: number, _height: number, _updateStyle?: boolean) {}
    render(_scene: unknown, camera: OrthographicCameraMock) {
      estado.vistas.push({ x: camera.position.x, y: camera.position.y, z: camera.position.z, zoom: camera.zoom })
    }
    dispose() {}
  }
  return {
    ACESFilmicToneMapping: 1,
    Box3: Box3Mock,
    Color: class { constructor(public value: string) {} },
    DirectionalLight: class { position = new Vector3Mock(); dispose() {} },
    HemisphereLight: class { dispose() {} },
    LoadingManager: class { setURLModifier(_fn: (url: string) => string) {} },
    OrthographicCamera: OrthographicCameraMock,
    PMREMGenerator: class {
      constructor(_renderer: WebGLRendererMock) {}
      fromScene(_scene: unknown) { return { texture: {} } }
      dispose() {}
    },
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
      return { scene: { position: { sub() {} }, traverse() {}, dispose() {} } }
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

function ultimaVista() {
  const vista = estado.vistas.at(-1)
  if (!vista) throw new Error('No se registró ninguna renderización')
  return vista
}

async function montar(cajaMm?: string) {
  estado.vistas.length = 0
  estado.descargas.length = 0
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
