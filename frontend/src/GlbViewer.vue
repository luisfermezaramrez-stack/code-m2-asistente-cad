<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { activeTheme } from './design/theme'
import { ACESFilmicToneMapping, AlwaysStencilFunc, BackSide, Box3, Color, DecrementWrapStencilOp,
  DirectionalLight, DoubleSide, FrontSide, Group, HemisphereLight, IncrementWrapStencilOp, Mesh,
  MeshBasicMaterial, NotEqualStencilFunc, OrthographicCamera, Plane, PlaneGeometry, PMREMGenerator,
  ReplaceStencilOp, Scene, Spherical, Vector3, WebGLRenderer, type WebGLRenderTarget, type Object3D,
  type Material, LoadingManager } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { EJES_CORTE, ETIQUETAS_CORTE, TECLAS_CORTE, constanteCorte, dimensionCorte, estadoInicialCorte,
  etiquetaCorte, fijarPosicion, limitesCorte, normalCorte, posicionMedia, type EstadoCorte,
  type EjeCorte } from './viewerCortes'
import { ETIQUETAS_EJE, ETIQUETAS_VISTA, VISTAS, formatearMedida, medidasCaja, nombreArchivo, parseCajaMm,
  posicionVista, type CajaMm, type Unidad, type Vista, type VistaActiva } from './viewerMedidas'

const props = defineProps<{ url: string; token: string; cajaMm?: string }>()
const host = ref<HTMLDivElement>()
const error = ref('')
const loading = ref(true)
const capturaError = ref('')
const vistaActual = ref<VistaActiva>('frontal')
const unidad = ref<Unidad>('mm')
const caja = computed(() => parseCajaMm(props.cajaMm))
const medidas = computed(() => (caja.value ? medidasCaja(caja.value, unidad.value) : []))
const cajaGeometrica = ref<CajaMm | null>(null)
const cajaCorte = computed(() => cajaGeometrica.value ?? caja.value)
const corte = ref<EstadoCorte>(estadoInicialCorte())
const limitesCorteActual = computed(() => limitesCorte(cajaCorte.value, corte.value.eje))
const pasoCorte = computed(() => Math.max(limitesCorteActual.value.max / 100, 0.01))
const posicionCorte = computed(() => fijarPosicion(cajaCorte.value, corte.value.eje, corte.value.posicion))
const valorPosicionCorte = computed(() => formatearMedida(posicionCorte.value, unidad.value))
const textoCorte = computed(() =>
  etiquetaCorte({ ...corte.value, posicion: posicionCorte.value }, cajaCorte.value, unidad.value),
)
const etiquetasVista = ETIQUETAS_VISTA
const etiquetasEje = ETIQUETAS_EJE
const ejesCorte = EJES_CORTE
const etiquetasCorte = ETIQUETAS_CORTE
let cleanup = () => {}
let turn = (_horizontal: number, _vertical = 0) => {}
let zoom = (_factor: number) => {}
let reset = () => {}
let refreshBackground = () => {}
let aplicarVista = (_vista: Vista) => {}
let aplicarCorte = (_estado: EstadoCorte) => {}
let capturar = () => {}

function dispose(object: Object3D) {
  object.traverse((child) => {
    const mesh = child as Mesh
    mesh.geometry?.dispose()
    const materials = mesh.material ? (Array.isArray(mesh.material) ? mesh.material : [mesh.material]) : []
    for (const material of materials) {
      for (const value of Object.values(material)) {
        if (value && typeof value === 'object' && 'isTexture' in value && value.isTexture) value.dispose()
      }
      ;(material as Material).dispose()
    }
  })
}

function activarCorte(eje: EjeCorte = corte.value.eje) {
  corte.value = { activo: true, eje, posicion: posicionMedia(cajaCorte.value, eje), invertido: false }
  aplicarCorte(corte.value)
}

function desactivarCorte() {
  corte.value = { ...corte.value, activo: false }
  aplicarCorte(corte.value)
}

function alternarCorte() {
  if (corte.value.activo) desactivarCorte()
  else activarCorte()
}

function invertirCorte() {
  if (!corte.value.activo) return
  corte.value = { ...corte.value, invertido: !corte.value.invertido }
  aplicarCorte(corte.value)
}

function cambiarPosicion(valor: number) {
  if (!corte.value.activo) return
  corte.value = { ...corte.value, posicion: fijarPosicion(cajaCorte.value, corte.value.eje, valor) }
  aplicarCorte(corte.value)
}

function alMoverCorte(evento: Event) {
  cambiarPosicion(Number((evento.target as HTMLInputElement).value))
}

function moverCorte(delta: number) {
  cambiarPosicion(posicionCorte.value + delta)
}

watch(() => [props.url, props.token, host.value] as const, async ([url, token, element], _old, onCleanup) => {
  cleanup()
  if (!element) return
  const control = new AbortController()
  let active = true
  let renderer: WebGLRenderer | undefined
  let controls: OrbitControls | undefined
  let model: Object3D | undefined
  let observer: ResizeObserver | undefined
  let environment: WebGLRenderTarget | undefined
  let plano: Plane | undefined
  let tapa: Group | undefined
  let mallaTapa: Mesh | undefined
  let estencil: Group | undefined
  let materialCara: MeshBasicMaterial | undefined
  error.value = ''; loading.value = true; capturaError.value = ''
  corte.value = estadoInicialCorte(); cajaGeometrica.value = null
  cleanup = () => {
    if (!active) return
    active = false; control.abort(); observer?.disconnect(); controls?.dispose(); refreshBackground = () => {}
    aplicarVista = () => {}; aplicarCorte = () => {}; turn = () => {}; zoom = () => {}; reset = () => {}
    capturar = () => {}
    if (model) dispose(model)
    if (estencil) dispose(estencil)
    if (tapa) dispose(tapa)
    environment?.dispose(); renderer?.dispose(); renderer?.domElement.remove()
  }
  onCleanup(cleanup)
  try {
    renderer = new WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true })
    renderer.localClippingEnabled = true
    renderer.toneMapping = ACESFilmicToneMapping
    renderer.toneMappingExposure = 0.65
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    const scene = new Scene()
    scene.background = new Color(getComputedStyle(document.documentElement).getPropertyValue('--color-viewer-background').trim())
    scene.add(new HemisphereLight(0xffffff, 0x465a70, 3))
    const light = new DirectionalLight(0xffffff, 3)
    light.position.set(1, 2, 3); scene.add(light)
    const room = new RoomEnvironment()
    const pmrem = new PMREMGenerator(renderer)
    environment = pmrem.fromScene(room)
    scene.environment = environment.texture
    room.dispose(); pmrem.dispose()
    const camera = new OrthographicCamera(-1, 1, 1, -1, 0.01, 10000)
    controls = new OrbitControls(camera, renderer.domElement)
    const render = () => { if (active) renderer?.render(scene, camera) }
    refreshBackground = () => {
      const value = getComputedStyle(document.documentElement).getPropertyValue('--color-viewer-background').trim()
      if (!value) return
      scene.background = new Color(value)
      const accent = getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim()
      if (accent && materialCara) materialCara.color = new Color(accent)
      render()
    }
    controls.addEventListener('change', render)
    element.append(renderer.domElement)
    renderer.domElement.setAttribute('aria-hidden', 'true')
    const response = await fetch(url, { signal: control.signal, headers: { 'X-Download-Token': token } })
    if (!response.ok) throw new Error('No se pudo cargar el modelo.')
    const manager = new LoadingManager()
    manager.setURLModifier((resource) => {
      if (resource.startsWith('blob:') || resource.startsWith('data:')) return resource
      throw new Error('El modelo requiere recursos externos no disponibles.')
    })
    const gltf = await new GLTFLoader(manager).parseAsync(await response.arrayBuffer(), '')
    if (!active) { dispose(gltf.scene); return }
    model = gltf.scene
    const box = new Box3().setFromObject(model)
    const center = box.getCenter(new Vector3())
    const tamanio = box.getSize(new Vector3())
    const radio = tamanio.length()
    if (!Number.isFinite(radio) || radio <= 0) throw new Error('Modelo sin geometría visible.')
    cajaGeometrica.value = { ancho: tamanio.x, fondo: tamanio.y, alto: tamanio.z }
    model.position.sub(center)
    scene.add(model)
    camera.near = radio / 1000; camera.far = radio * 100
    controls.minZoom = 0.3; controls.maxZoom = 8
    const actualizarFrustum = () => {
      const relacion = Math.max(element.clientWidth, 1) / 288
      const altura = radio * 1.5
      camera.left = -altura * relacion / 2
      camera.right = altura * relacion / 2
      camera.top = altura / 2
      camera.bottom = -altura / 2
      camera.updateProjectionMatrix()
    }
    aplicarVista = (vista) => {
      vistaActual.value = vista
      const [x = 0, y = 0, z = 0] = posicionVista(vista, radio)
      camera.position.set(x, y, z)
      camera.zoom = 1
      camera.updateProjectionMatrix()
      controls?.target.set(0, 0, 0); controls?.update(); render()
    }
    reset = () => aplicarVista('frontal')
    turn = (horizontal, vertical = 0) => {
      const spherical = new Spherical().setFromVector3(camera.position)
      spherical.theta += horizontal
      spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + vertical))
      camera.position.setFromSpherical(spherical); controls?.update(); render()
      vistaActual.value = 'libre'
    }
    zoom = (factor) => {
      camera.zoom = Math.max(0.3, Math.min(8, camera.zoom / factor))
      camera.updateProjectionMatrix(); controls?.update(); render()
    }
    plano = new Plane(new Vector3(0, 0, 1), 0)
    const materialesModelo: Material[] = []
    model.traverse((child) => {
      const malla = child as Mesh
      const material = malla.material
      for (const item of material ? (Array.isArray(material) ? material : [material]) : []) materialesModelo.push(item)
    })
    estencil = new Group()
    for (const [lado, operacion, orden] of [
      [BackSide, IncrementWrapStencilOp, 1],
      [FrontSide, DecrementWrapStencilOp, 2],
    ] as const) {
      const materialStencil = new MeshBasicMaterial({
        colorWrite: false, depthWrite: false, depthTest: false,
        stencilWrite: true, stencilFunc: AlwaysStencilFunc, side: lado,
        clippingPlanes: [plano],
      })
      materialStencil.stencilFail = operacion
      materialStencil.stencilZFail = operacion
      materialStencil.stencilZPass = operacion
      model.traverse((child) => {
        const malla = child as Mesh
        if (!malla.geometry) return
        const copia = new Mesh(malla.geometry, materialStencil)
        copia.renderOrder = orden
        estencil?.add(copia)
      })
    }
    const accent = getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim()
    materialCara = new MeshBasicMaterial({
      color: new Color(accent || '#ff9f1c'), side: DoubleSide,
      stencilWrite: true, stencilRef: 0, stencilFunc: NotEqualStencilFunc,
      stencilFail: ReplaceStencilOp, stencilZFail: ReplaceStencilOp, stencilZPass: ReplaceStencilOp,
    })
    mallaTapa = new Mesh(new PlaneGeometry(1, 1), materialCara)
    mallaTapa.renderOrder = 3
    mallaTapa.onAfterRender = (renderizador: WebGLRenderer) => renderizador.clearStencil()
    tapa = new Group()
    tapa.add(mallaTapa)
    scene.add(estencil)
    scene.add(tapa)
    aplicarCorte = (estado) => {
      if (!plano || !tapa || !estencil || !mallaTapa) return
      const [x, y, z] = normalCorte(estado.eje, estado.invertido)
      plano.normal.set(x, y, z)
      plano.constant = constanteCorte(cajaCorte.value, estado)
      const ancho = dimensionCorte(cajaCorte.value, 'x')
      const fondo = dimensionCorte(cajaCorte.value, 'y')
      const alto = dimensionCorte(cajaCorte.value, 'z')
      const desplazamiento = fijarPosicion(cajaCorte.value, estado.eje, estado.posicion) -
        dimensionCorte(cajaCorte.value, estado.eje) / 2
      mallaTapa.rotation.set(0, 0, 0)
      if (estado.eje === 'x') {
        mallaTapa.rotation.set(0, Math.PI / 2, 0)
        mallaTapa.scale.set(alto, fondo, 1)
        mallaTapa.position.set(desplazamiento, 0, 0)
      } else if (estado.eje === 'y') {
        mallaTapa.rotation.set(-Math.PI / 2, 0, 0)
        mallaTapa.scale.set(ancho, alto, 1)
        mallaTapa.position.set(0, desplazamiento, 0)
      } else {
        mallaTapa.scale.set(ancho, fondo, 1)
        mallaTapa.position.set(0, 0, desplazamiento)
      }
      tapa.visible = estado.activo
      mallaTapa.visible = estado.activo
      estencil.visible = estado.activo
      for (const material of materialesModelo) {
        const teniaPlano = (material.clippingPlanes?.length ?? 0) > 0
        material.clippingPlanes = estado.activo ? [plano] : []
        if (teniaPlano !== estado.activo) material.needsUpdate = true
      }
      render()
    }
    capturar = () => {
      if (!renderer || !active) return
      try {
        render()
        const png = renderer.domElement.toDataURL('image/png')
        if (!png.startsWith('data:image/png;base64,') || png.length < 32) throw new Error('Lienzo vacío.')
        capturaError.value = ''
        const enlace = document.createElement('a')
        enlace.href = png
        enlace.download = nombreArchivo(vistaActual.value, unidad.value)
        document.body.appendChild(enlace)
        enlace.click()
        enlace.remove()
      } catch {
        capturaError.value = 'No se pudo capturar la vista en este navegador.'
      }
    }
    const resize = () => {
      renderer?.setSize(element.clientWidth, 288, false)
      actualizarFrustum(); render()
    }
    observer = new ResizeObserver(resize); observer.observe(element)
    reset(); resize(); aplicarCorte(corte.value); loading.value = false
  } catch {
    if (active) {
      error.value = 'La vista 3D no está disponible en este navegador o el archivo no se pudo abrir. Las descargas siguen disponibles.'
      loading.value = false
    }
  }
}, { flush: 'post', immediate: true })

watch(activeTheme, () => refreshBackground())

const teclasVista: Record<string, Vista> = { '1': 'frontal', '2': 'superior', '3': 'lateral' }

function key(event: KeyboardEvent) {
  const vista = teclasVista[event.key]
  if (vista) { event.preventDefault(); aplicarVista(vista); return }
  const ejeCorte = TECLAS_CORTE[event.key]
  if (ejeCorte) { event.preventDefault(); activarCorte(ejeCorte); return }
  const tecla = event.key.toLowerCase()
  if (tecla === 'u') { event.preventDefault(); unidad.value = unidad.value === 'mm' ? 'in' : 'mm'; return }
  if (tecla === 'c') { event.preventDefault(); alternarCorte(); return }
  if (tecla === 'i') { event.preventDefault(); invertirCorte(); return }
  const actions: Record<string, () => void> = {
    ArrowLeft: () => turn(-0.2), ArrowRight: () => turn(0.2),
    ArrowUp: () => turn(0, -0.2), ArrowDown: () => turn(0, 0.2),
    '+': () => zoom(0.85), '-': () => zoom(1.15), Home: () => reset(),
    ']': () => moverCorte(pasoCorte.value), '[': () => moverCorte(-pasoCorte.value),
  }
  if (actions[event.key]) { event.preventDefault(); actions[event.key]?.() }
}
onBeforeUnmount(() => cleanup())
</script>

<template>
  <div class="model-viewer">
    <p v-if="loading" role="status">Cargando vista 3D…</p>
    <p v-if="error" role="status" class="help">{{ error }}</p>
    <div ref="host" class="model-canvas" :tabindex="error || loading ? -1 : 0" role="group" aria-label="Vista 3D de la pieza" aria-describedby="viewer-help" @keydown="key" />
    <p id="viewer-help" class="help">Flechas para girar; + y − para acercar o alejar; Inicio para restablecer; 1, 2 y 3 para vistas ortogonales; 4, 5 y 6 para cortar por X, Y y Z; C activa o desactiva el corte; I lo invierte; [ y ] lo desplaza; U cambia unidades. También puedes usar los botones.</p>
    <template v-if="!error && !loading">
      <div class="actions viewer-actions" role="group" aria-label="Vistas ortogonales">
        <button v-for="vista in VISTAS" :key="vista" type="button" :aria-pressed="vistaActual === vista" @click="aplicarVista(vista)">{{ etiquetasVista[vista] }}</button>
      </div>
      <div class="actions viewer-actions">
        <button type="button" @click="turn(-0.2)">Girar izquierda</button>
        <button type="button" @click="turn(0.2)">Girar derecha</button>
        <button type="button" @click="zoom(0.85)">Acercar</button>
        <button type="button" @click="zoom(1.15)">Alejar</button>
        <button type="button" @click="reset()">Restablecer vista</button>
        <button type="button" @click="capturar()">Capturar PNG</button>
      </div>
      <div class="actions cortes" role="group" aria-label="Cortes y secciones">
        <button v-for="eje in ejesCorte" :key="eje" type="button"
          :aria-pressed="corte.activo && corte.eje === eje" @click="activarCorte(eje)">
          Cortar {{ etiquetasCorte[eje] }}
        </button>
        <button type="button" :aria-pressed="corte.activo" @click="alternarCorte()">
          {{ corte.activo ? 'Desactivar corte' : 'Activar corte' }}
        </button>
        <button type="button" :aria-pressed="corte.invertido" :disabled="!corte.activo" @click="invertirCorte()">
          Invertir corte
        </button>
        <label for="posicion-corte">Posición del corte</label>
        <input id="posicion-corte" type="range" :min="limitesCorteActual.min" :max="limitesCorteActual.max"
          :step="pasoCorte" :value="posicionCorte" :disabled="!corte.activo"
          :aria-valuetext="valorPosicionCorte" @input="alMoverCorte">
        <p class="help" role="status" aria-live="polite">{{ textoCorte }}</p>
      </div>
      <p v-if="capturaError" role="alert" class="field-error">{{ capturaError }}</p>
      <div class="medidas">
        <label for="unidad-medidas">Unidades de las cotas</label>
        <select id="unidad-medidas" v-model="unidad">
          <option value="mm">Milímetros (mm)</option>
          <option value="in">Pulgadas (in)</option>
        </select>
        <dl v-if="medidas.length" aria-label="Cotas generales de la pieza">
          <div v-for="medida in medidas" :key="medida.eje">
            <dt>{{ etiquetasEje[medida.eje] }}</dt>
            <dd>{{ medida.texto }}</dd>
          </div>
        </dl>
        <p v-else class="help">Cotas no disponibles: el resultado no informó `caja_mm`.</p>
      </div>
    </template>
  </div>
</template>
