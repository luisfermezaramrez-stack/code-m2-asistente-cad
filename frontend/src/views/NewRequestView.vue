<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, ref } from 'vue'
import type { Stage } from '../api'
import { useGenerationContext } from '../useGeneration'

const props = defineProps<{ necesitaLogin: boolean }>()

const GlbViewer = defineAsyncComponent(() => import('../GlbViewer.vue'))
// El estado de generación pertenece al shell: navegar no aborta el trabajo en curso.
const flow = useGenerationContext()
const { description, timeoutSeconds, job, stages, artifacts, busy, checking, cancelling, loadingFiles,
  message, inputError, filesError, disconnected, canCancel, canCheck, downloadToken } = flow
const input = ref<HTMLTextAreaElement>()
const labels: Record<Stage, string> = {
  iniciando: 'Esperando información', validando: 'Validando solicitud', generando: 'Generando pieza',
  verificado: 'Pieza verificada', declinado: 'Solicitud declinada', error: 'No se pudo completar',
  cancelado: 'Procesamiento local detenido',
}
const status = computed(() => {
  if (job.value?.terminal) return labels[job.value.estado]
  if (cancelling.value) return 'Solicitando cancelación'
  if (job.value?.cancelacion_solicitada) return 'Cancelación solicitada'
  if (disconnected.value) return 'Conexión interrumpida'
  if (job.value) return labels[job.value.estado]
  return busy.value ? 'Esperando información' : 'Sin solicitud'
})
const glb = computed(() => artifacts.value.find((item) => item.format === 'glb'))
const hasStep = computed(() => artifacts.value.some((item) => item.format === 'step'))

async function submit() {
  if (props.necesitaLogin) return
  const run = flow.start()
  await nextTick()
  if (inputError.value) input.value?.focus()
  await run
}
</script>

<template>
  <div class="workspace">
    <section class="panel" aria-labelledby="request-title">
      <h2 id="request-title">Describe tu pieza</h2>
      <form novalidate @submit.prevent="submit">
        <label for="descripcion">Descripción técnica</label>
        <textarea id="descripcion" ref="input" v-model="description" maxlength="1000" :readonly="busy" :aria-invalid="!!inputError" aria-describedby="input-help input-error" placeholder="Ej.: placa de 120 × 120 mm, espesor de 6 mm y 4 agujeros de 12 mm en un círculo de 90 mm." />
        <p id="input-help" class="help">Entre 1 y 1000 caracteres. Incluye dimensiones, unidades y material si lo conoces.</p>
        <p id="input-error" class="field-error" role="alert">{{ inputError }}</p>
        <details class="settings"><summary>Opciones de espera</summary>
          <label for="timeout">Tiempo máximo de espera (segundos)</label>
          <input id="timeout" v-model.number="timeoutSeconds" type="number" min="5" max="600" step="1" :disabled="busy" aria-describedby="timeout-help">
          <p id="timeout-help" class="help">De 5 a 600 segundos. Interrumpir la espera desconecta y solicita cancelación local; consulta el estado para confirmar la detención. No se confirma la detención de servicios remotos.</p>
        </details>
        <div class="actions">
          <button class="primary" type="submit" :disabled="busy || props.necesitaLogin">Generar pieza</button>
          <button type="button" :disabled="!canCancel" @click="flow.cancel">Cancelar solicitud</button>
        </div>
      </form>
      <div v-if="busy || canCheck" class="actions">
        <button v-if="busy" type="button" @click="flow.stopWaiting">Interrumpir espera</button>
        <button v-if="canCheck" type="button" :disabled="checking" @click="flow.refresh">{{ checking ? 'Consultando estado…' : 'Actualizar estado' }}</button>
      </div>
    </section>
    <div class="stack">
      <section class="panel" aria-labelledby="process-title">
        <h2 id="process-title">Proceso</h2>
        <div class="state" :class="job?.estado ?? 'idle'" aria-live="polite" aria-atomic="true">
          <strong>{{ status }}</strong>
          <p v-if="job?.cancelacion_solicitada && !job.terminal">Esperando que el procesamiento alcance un punto seguro para detenerse.</p>
          <p v-if="message">{{ message }}</p>
        </div>
        <ol v-if="stages.length" class="steps" aria-label="Etapas informadas">
          <li v-for="stage in stages" :key="stage">{{ labels[stage] }}</li>
        </ol>
        <p v-if="!stages.length && (busy || disconnected)" class="help">El servicio aún no informa progreso. No se puede confirmar la etapa actual.</p>
        <p v-if="!stages.length && !busy && !disconnected" class="muted">Escribe una descripción para comenzar.</p>
      </section>
      <section class="panel" aria-labelledby="preview-title">
        <h2 id="preview-title">Vista 3D</h2>
        <GlbViewer v-if="glb" :key="glb.url" :url="glb.url" :token="downloadToken" :caja-mm="job?.resultado?.caja_mm" />
        <div v-else class="viewport">
          <h3>{{ job?.estado === 'verificado' ? 'Vista 3D no disponible' : 'Aún no hay una pieza' }}</h3>
          <p class="muted">{{ job?.estado === 'verificado' ? 'Puedes descargar el STEP si está disponible, aunque no exista una vista 3D.' : 'El modelo aparecerá cuando la pieza esté lista y exista un archivo de vista 3D.' }}</p>
        </div>
      </section>
      <section class="panel" aria-labelledby="downloads-title">
        <h2 id="downloads-title">Archivos de la pieza</h2>
        <p v-if="loadingFiles" role="status">Comprobando archivos disponibles…</p>
        <p v-if="filesError" role="status" class="field-error">{{ filesError }}</p>
        <div v-if="artifacts.length" class="downloads">
          <button v-for="file in artifacts" :key="file.format" type="button" class="download" :data-download-url="file.url" :data-download-filename="`pieza.${file.format}`" @click="flow.download(file)">
            <strong>{{ file.format === 'csv' ? 'Materiales (CSV)' : file.format.toUpperCase() }}</strong>
            <span>Descargar {{ file.format === 'csv' ? 'lista de materiales' : file.format.toUpperCase() }}</span>
          </button>
        </div>
        <p v-else-if="!loadingFiles" class="muted">No hay archivos disponibles.</p>
        <p v-if="job?.estado === 'verificado' && !loadingFiles && !hasStep" class="help">No hay archivo STEP disponible.</p>
      </section>
    </div>
  </div>
</template>
