<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { ACESFilmicToneMapping, Box3, Color, DirectionalLight, HemisphereLight, PerspectiveCamera, PMREMGenerator,
  Scene, Spherical, Vector3, WebGLRenderer, type WebGLRenderTarget,
  type Object3D, type Mesh, type Material, LoadingManager } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'

const props = defineProps<{ url: string }>()
const host = ref<HTMLDivElement>()
const error = ref('')
const loading = ref(true)
let cleanup = () => {}
let turn = (_horizontal: number, _vertical = 0) => {}
let zoom = (_factor: number) => {}
let reset = () => {}

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

watch(() => [props.url, host.value] as const, async ([url, element], _old, onCleanup) => {
  cleanup()
  if (!element) return
  const control = new AbortController()
  let active = true
  let renderer: WebGLRenderer | undefined
  let controls: OrbitControls | undefined
  let model: Object3D | undefined
  let observer: ResizeObserver | undefined
  let environment: WebGLRenderTarget | undefined
  error.value = ''; loading.value = true
  cleanup = () => {
    if (!active) return
    active = false; control.abort(); observer?.disconnect(); controls?.dispose()
    if (model) dispose(model)
    environment?.dispose(); renderer?.dispose(); renderer?.domElement.remove()
  }
  onCleanup(cleanup)
  try {
    renderer = new WebGLRenderer({ antialias: true, alpha: false })
    renderer.toneMapping = ACESFilmicToneMapping
    renderer.toneMappingExposure = 0.65
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    const scene = new Scene()
    scene.background = new Color(getComputedStyle(document.documentElement).getPropertyValue('--color-surface-subtle').trim())
    scene.add(new HemisphereLight(0xffffff, 0x465a70, 3))
    const light = new DirectionalLight(0xffffff, 3)
    light.position.set(1, 2, 3); scene.add(light)
    // Los metales necesitan un entorno para reflejar luz; se genera localmente.
    const room = new RoomEnvironment()
    const pmrem = new PMREMGenerator(renderer)
    environment = pmrem.fromScene(room)
    scene.environment = environment.texture
    room.dispose(); pmrem.dispose()
    const camera = new PerspectiveCamera(40, 1, 0.01, 10000)
    controls = new OrbitControls(camera, renderer.domElement)
    const render = () => { if (active) renderer?.render(scene, camera) }
    controls.addEventListener('change', render)
    element.append(renderer.domElement)
    renderer.domElement.setAttribute('aria-hidden', 'true')
    const response = await fetch(url, { signal: control.signal })
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
    const size = box.getSize(new Vector3()).length()
    if (!Number.isFinite(size) || size <= 0) throw new Error('Modelo sin geometría visible.')
    model.position.sub(center)
    scene.add(model)
    camera.near = size / 1000; camera.far = size * 100
    controls.minDistance = size / 10; controls.maxDistance = size * 10
    reset = () => {
      camera.position.set(size, size * 0.7, size)
      controls?.target.set(0, 0, 0); controls?.update(); render()
    }
    turn = (horizontal, vertical = 0) => {
      const spherical = new Spherical().setFromVector3(camera.position)
      spherical.theta += horizontal
      spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + vertical))
      camera.position.setFromSpherical(spherical); controls?.update(); render()
    }
    zoom = (factor) => {
      const distance = Math.max(size / 10, Math.min(size * 10, camera.position.length() * factor))
      camera.position.setLength(distance); controls?.update(); render()
    }
    const resize = () => {
      const width = element.clientWidth
      renderer?.setSize(width, 288, false)
      camera.aspect = width / 288; camera.updateProjectionMatrix(); render()
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

function key(event: KeyboardEvent) {
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
    <p id="viewer-help" class="help">Flechas para girar; + y − para acercar o alejar; Inicio para restablecer. También puedes usar los botones.</p>
    <template v-if="!error && !loading">
      <div class="actions viewer-actions">
        <button type="button" @click="turn(-0.2)">Girar izquierda</button>
        <button type="button" @click="turn(0.2)">Girar derecha</button>
        <button type="button" @click="zoom(0.85)">Acercar</button>
        <button type="button" @click="zoom(1.15)">Alejar</button>
        <button type="button" @click="reset()">Restablecer vista</button>
      </div>
    </template>
  </div>
</template>
