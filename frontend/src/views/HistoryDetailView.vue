<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  consultarRegistro, downloadArtifact, glbVivo, publicMessage, stepRegistro, validarEstado,
  type Artifact, type EstadoRegistro, type FilaRegistro,
} from '../api'

const GlbViewer = defineAsyncComponent(() => import('../GlbViewer.vue'))
const route = useRoute()
const etiquetas: Record<EstadoRegistro, string> = {
  construida: 'Construida', declinada: 'Declinada', error: 'Error', desconocida: 'Desconocida',
}
const identificador = computed(() => String(route.params.identificador ?? ''))
const fila = ref<FilaRegistro | null>(null)
const token = ref('')
const cargando = ref(true)
const error = ref('')
const aviso = ref('Cargando la solicitud…')
const descargando = ref(false)
const glb = ref<Artifact | null>(null)
let control: AbortController | undefined

// `estado` y `motivo` los deriva el backend (RNF-1): la vista no repite la regla.
const estado = computed<EstadoRegistro | null>(() => (fila.value ? validarEstado(fila.value.estado) : null))
const motivo = computed(() => fila.value?.motivo ?? '')
// El STEP de una solicitud anterior vive en el registro, no en el trabajo en curso.
const step = computed<Artifact | null>(() => (estado.value === 'construida' ? stepRegistro(identificador.value) : null))

async function cargar() {
  control?.abort()
  const actual = new AbortController()
  control = actual
  cargando.value = true
  error.value = ''
  aviso.value = 'Cargando la solicitud…'
  fila.value = null
  glb.value = null
  try {
    const consultado = await consultarRegistro(identificador.value, actual.signal)
    if (actual.signal.aborted) return
    fila.value = consultado.fila
    token.value = consultado.token
    cargando.value = false
    aviso.value = 'Solicitud reabierta.'
    if (validarEstado(consultado.fila.estado) !== 'construida') return
    // GLB y CSV sólo se ofrecen mientras el trabajo siga vivo en el servidor (RF-4).
    glb.value = await glbVivo(identificador.value, consultado.token, actual.signal)
  } catch (fallo) {
    if (actual.signal.aborted) return
    fila.value = null
    glb.value = null
    error.value = publicMessage(fallo instanceof Error ? fallo.message : '', 'No se pudo consultar la solicitud.')
    aviso.value = error.value
  } finally {
    if (!actual.signal.aborted) cargando.value = false
  }
}

async function descargar() {
  if (!step.value) return
  descargando.value = true
  aviso.value = 'Descargando el STEP…'
  try {
    await downloadArtifact(step.value, token.value)
    aviso.value = 'Descarga del STEP solicitada.'
  } catch (fallo) {
    aviso.value = publicMessage(fallo instanceof Error ? fallo.message : '', 'No se pudo descargar el archivo.')
  } finally {
    descargando.value = false
  }
}

onMounted(cargar)
// La ruta reutiliza la instancia al cambiar de identificador: hay que recargar.
watch(identificador, () => { void cargar() })
onBeforeUnmount(() => control?.abort())
</script>

<template>
  <section class="panel" aria-labelledby="solicitud-title">
    <h2 id="solicitud-title">Solicitud reabierta</h2>
    <p class="help" aria-live="polite" role="status">{{ aviso }}</p>
    <div v-if="error" class="state error" role="alert">{{ error }}</div>
    <template v-else-if="fila && estado">
      <p class="registro-meta">
        <time :datetime="fila.hora">{{ fila.hora }}</time>
        <strong class="registro-estado">{{ etiquetas[estado] }}</strong>
      </p>
      <p class="registro-texto">{{ fila.texto }}</p>
      <p v-if="motivo" class="motivo">{{ motivo }}</p>
      <div class="actions">
        <button
          v-if="step"
          type="button"
          class="download"
          :data-download-url="step.url"
          data-download-filename="pieza.step"
          :disabled="descargando"
          @click="descargar"
        >
          <strong>STEP</strong>
          <span>Descargar STEP</span>
        </button>
        <RouterLink class="volver" to="/historial">Volver al historial</RouterLink>
      </div>
      <GlbViewer v-if="glb" :key="glb.url" :url="glb.url" :token="token" />
      <p v-else-if="step" class="muted">
        La vista 3D de una solicitud anterior sólo aparece mientras el trabajo siga vivo en el servidor.
      </p>
    </template>
  </section>
</template>

<style scoped>
.registro-meta { display: flex; flex-wrap: wrap; gap: var(--space-3); justify-content: space-between; color: var(--color-muted); font-size: var(--text-small); }
.registro-estado { color: var(--color-text); }
.motivo { color: var(--color-warning); }
.volver { display: inline-flex; align-items: center; min-height: var(--control-min); }
</style>
