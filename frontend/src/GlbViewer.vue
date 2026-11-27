<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { activeTheme } from './design/theme'
import { ACESFilmicToneMapping, Box3, Color, DirectionalLight, HemisphereLight, OrthographicCamera, PMREMGenerator,
  Scene, Spherical, Vector3, WebGLRenderer, type WebGLRenderTarget,
  type Object3D, type Mesh, type Material, LoadingManager } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { ETIQUETAS_EJE, ETIQUETAS_VISTA, VISTAS, medidasCaja, nombreArchivo, parseCajaMm, posicionVista,
  type Unidad, type Vista, type VistaActiva } from './viewerMedidas'

const props = defineProps<{ url: string; token: string; cajaMm?: string }>()
const host = ref<HTMLDivElement>()
const error = ref('')
const loading = ref(true)
const capturaError = ref('')
const vistaActual = ref<VistaActiva>('frontal')
const unidad = ref<Unidad>('mm')
const caja = computed(() => parseCajaMm(props.cajaMm))
const medidas = computed(() => (caja.value ? medidasCaja(caja.value, unidad.value) : []))
const etiquetasVista = ETIQUETAS_VISTA
const etiquetasEje = ETIQUETAS_EJE
let cleanup = () => {}
let turn = (_horizontal: number, _vertical = 0) => {}
let zoom = (_factor: number) => {}
let reset = () => {}
let refreshBackground = () => {}
let aplicarVista = (_vista: Vista) => {}
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
  error.value = ''; loading.value = true; capturaError.value = ''
  cleanup = () => {
    if (!active) return
    active = false; control.abort(); observer?.disconnect(); controls?.dispose(); refreshBackground = () => {}
    aplicarVista = () => {}; capturar = () => {}
    if (model) dispose(model)
    environment?.dispose(); renderer?.dispose(); renderer?.domElement.remove()
  }
  onCleanup(cleanup)
  try {
    renderer = new WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true })
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
    const radio = box.getSize(new Vector3()).length()
    if (!Number.isFinite(radio) || radio <= 0) throw new Error('Modelo sin geometría visible.')
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
    reset(); resize(); loading.value = false
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
  if (event.key.toLowerCase() === 'u') { event.preventDefault(); unidad.value = unidad.value === 'mm' ? 'in' : 'mm'; return }
  const actions: Record<string, () => void> = {
    ArrowLeft: () => turn(-0.2), ArrowRight: () => turn(0.2),
    ArrowUp: () => turn(0, -0.2), ArrowDown: () => turn(0, 0.2),
    '+': () => zoom(0.85), '-': () => zoom(1.15), Home: () => reset(),
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
    <p id="viewer-help" class="help">Flechas para girar; + y − para acercar o alejar; Inicio para restablecer; 1, 2 y 3 para vistas ortogonales; U para cambiar unidades. También puedes usar los botones.</p>
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
