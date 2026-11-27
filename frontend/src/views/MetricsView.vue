<script setup lang="ts">
// Panorama de métricas (HU-51, SPEC-052): tablas y cifras simples, sin gráficos.
import { computed, onMounted, ref } from 'vue'
import { cargarMetricas } from '../api'
import type { PanoramaMetricas } from '../api'

const panorama = ref<PanoramaMetricas | null>(null)
const error = ref('')
const cargando = ref(true)

const causas = computed(() => Object.entries(panorama.value?.declinaciones_por_causa ?? {}))
// R1-3: sólo un enlace http(s) se pinta; cualquier otro esquema del entorno se omite.
const mlflowUi = computed(() => {
  const valor = panorama.value?.mlflow_ui ?? ''
  return /^https?:\/\//i.test(valor) ? valor : null
})
const costo = computed(() => `USD ${(panorama.value?.costo_usd ?? 0).toFixed(4)}`)
const latencia = computed(() => {
  const valor = panorama.value?.latencia_media_ms
  return valor === null || valor === undefined ? 'sin datos' : `${valor.toFixed(0)} ms`
})

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    panorama.value = await cargarMetricas()
  } catch (fallo) {
    error.value = fallo instanceof Error ? fallo.message : 'No se pudieron leer las métricas.'
  }
  cargando.value = false
}

onMounted(cargar)
</script>

<template>
  <section class="panel" aria-labelledby="metricas-title">
    <h2 id="metricas-title">Métricas del servicio</h2>
    <p class="muted">Uso, calidad y costo de las generaciones registradas en la ventana.</p>

    <p v-if="cargando" role="status">Leyendo métricas…</p>
    <p v-else-if="error" class="field-error" role="alert">
      {{ error }}
      <button type="button" data-test="reintentar-error" @click="cargar">Reintentar</button>
    </p>

    <template v-else-if="panorama">
      <p v-if="!panorama.disponible" class="aviso-degradado" role="alert" data-test="degradado">
        <strong>Métricas no disponibles.</strong> {{ panorama.motivo }}
        <button type="button" @click="cargar">Reintentar</button>
      </p>

      <dl class="cifras">
        <div><dt>Solicitudes</dt><dd data-test="solicitudes">{{ panorama.solicitudes }}</dd></div>
        <div><dt>Piezas entregadas</dt><dd data-test="entregadas">{{ panorama.entregadas }}</dd></div>
        <div><dt>Declinaciones</dt><dd data-test="declinadas">{{ panorama.declinadas }}</dd></div>
        <div><dt>Errores</dt><dd data-test="errores">{{ panorama.errores }}</dd></div>
        <div><dt>Latencia media</dt><dd data-test="latencia">{{ latencia }}</dd></div>
        <div><dt>Costo acumulado</dt><dd data-test="costo">{{ costo }}</dd></div>
      </dl>

      <h3>Declinaciones por causa</h3>
      <p v-if="causas.length === 0" class="muted">Sin declinaciones en la ventana.</p>
      <table v-else class="causas">
        <thead><tr><th scope="col">Causa</th><th scope="col">Casos</th></tr></thead>
        <tbody>
          <tr v-for="[causa, total] in causas" :key="causa">
            <td>{{ causa }}</td>
            <td>{{ total }}</td>
          </tr>
        </tbody>
      </table>

      <p v-if="mlflowUi" class="detalle">
        Detalle por corrida en
        <a :href="mlflowUi" target="_blank" rel="noopener noreferrer" data-test="mlflow">la UI de MLflow</a>.
      </p>
      <p class="muted">Ventana: {{ panorama.desde }} — {{ panorama.hasta }}.</p>
    </template>
  </section>
</template>

<style scoped>
.cifras { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr)); gap: .75rem; margin: 1rem 0; }
.cifras dt { font-size: .8rem; color: var(--color-muted, #666); }
.cifras dd { margin: 0; font-size: 1.4rem; font-variant-numeric: tabular-nums; }
.causas { width: 100%; border-collapse: collapse; }
.causas th, .causas td { text-align: left; padding: .25rem .5rem; border-bottom: 1px solid var(--color-border, #ddd); }
.aviso-degradado { border-left: 3px solid var(--color-warning, #b8860b); padding-left: .5rem; }
.detalle { margin-top: 1rem; }
</style>
