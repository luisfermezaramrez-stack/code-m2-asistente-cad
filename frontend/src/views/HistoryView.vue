<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { listarRegistros, publicMessage, type EstadoRegistro, type RegistroResumen } from '../api'
import VistaEstado from '../components/VistaEstado.vue'
import type { EstadoVista } from '../estadosVista'

// Textos literales de la base de accesibilidad existente (HU-38, RNF-3).
const textos = {
  vacio: 'No hay solicitudes registradas para mostrar.',
  cargando: 'Cargando el historial…',
  error: 'No se pudo cargar el historial.',
}
const etiquetas: Record<EstadoRegistro, string> = {
  construida: 'Construida', declinada: 'Declinada', error: 'Error', desconocida: 'Desconocida',
}
const opciones: EstadoRegistro[] = ['construida', 'declinada', 'error', 'desconocida']

const filtroResultado = ref<'' | EstadoRegistro>('')
const filtroTexto = ref('')
const registros = ref<RegistroResumen[]>([])
const cargando = ref(true)
const error = ref('')
const anuncio = ref(textos.cargando)
let control: AbortController | undefined

// Sin `?estado=`: el historial se deriva de la carga real del backend (HU-37, S2).
const estadoVista = computed<EstadoVista | null>(() => {
  if (cargando.value) return 'cargando'
  if (error.value) return 'error'
  return registros.value.length ? null : 'vacio'
})

async function cargar() {
  control?.abort()
  const actual = new AbortController()
  control = actual
  cargando.value = true
  error.value = ''
  anuncio.value = textos.cargando
  try {
    const encontrados = await listarRegistros(
      { resultado: filtroResultado.value || null, texto: filtroTexto.value },
      actual.signal,
    )
    if (actual.signal.aborted) return
    registros.value = encontrados
    anuncio.value = encontrados.length
      ? `Historial actualizado: ${encontrados.length} ${encontrados.length === 1 ? 'solicitud' : 'solicitudes'}.`
      : textos.vacio
  } catch (fallo) {
    if (actual.signal.aborted) return
    registros.value = []
    error.value = publicMessage(fallo instanceof Error ? fallo.message : '', textos.error)
    anuncio.value = error.value
  } finally {
    if (!actual.signal.aborted) cargando.value = false
  }
}

function filtrar() { void cargar() }

onMounted(cargar)
onBeforeUnmount(() => control?.abort())
</script>

<template>
  <section class="panel" aria-labelledby="historial-title">
    <h2 id="historial-title">Historial</h2>
    <form class="filtros" aria-label="Filtros del historial" @submit.prevent="filtrar">
      <div>
        <label for="filtro-resultado">Resultado</label>
        <select id="filtro-resultado" v-model="filtroResultado">
          <option value="">Todos</option>
          <option v-for="estado in opciones" :key="estado" :value="estado">{{ etiquetas[estado] }}</option>
        </select>
      </div>
      <div>
        <label for="filtro-texto">Texto de la descripción</label>
        <input id="filtro-texto" v-model="filtroTexto" type="search" maxlength="200" placeholder="Ej.: placa de acero" />
      </div>
      <button type="submit">Filtrar</button>
    </form>
    <p class="help anuncio" aria-live="polite" role="status">{{ anuncio }}</p>
    <VistaEstado v-if="estadoVista" :estado="estadoVista" :textos="textos" />
    <ul v-else class="registros">
      <li v-for="registro in registros" :key="registro.id" class="registro">
        <p class="registro-meta">
          <time :datetime="registro.hora">{{ registro.hora }}</time>
          <strong class="registro-estado">{{ etiquetas[registro.estado] }}</strong>
        </p>
        <p class="registro-texto">{{ registro.texto }}</p>
        <p v-if="registro.motivo" class="motivo">{{ registro.motivo }}</p>
        <RouterLink class="reabrir" :to="`/historial/${registro.id}`">Reabrir</RouterLink>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.filtros { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: var(--space-3); align-items: end; margin-bottom: var(--space-4); }
.filtros button { justify-self: start; }
select { width: 100%; min-height: var(--control-min); padding: var(--space-2) var(--space-3); border: var(--border-width) solid var(--color-border); border-radius: var(--radius-small); color: var(--color-text); background: var(--color-surface); font: inherit; }
.anuncio { margin-bottom: var(--space-4); }
.registros { display: grid; gap: var(--space-4); margin: 0; padding: 0; list-style: none; }
.registro { padding: var(--space-4); border: var(--border-width) solid var(--color-border); border-radius: var(--radius-small); background: var(--color-surface-subtle); }
.registro p:last-of-type { margin-bottom: var(--space-3); }
.registro-meta { display: flex; flex-wrap: wrap; gap: var(--space-3); justify-content: space-between; color: var(--color-muted); font-size: var(--text-small); }
.registro-estado { color: var(--color-text); }
.motivo { color: var(--color-warning); }
.reabrir { display: inline-flex; align-items: center; min-height: var(--control-min); }
</style>
