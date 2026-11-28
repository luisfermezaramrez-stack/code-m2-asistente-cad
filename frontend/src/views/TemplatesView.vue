<script setup lang="ts">
// Plantillas parametrizadas (HU-49, SPEC-050, RF-5): elegir una plantilla, ajustar sus
// parámetros y generar la pieza sin llamar al modelo.
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  instanciarPlantilla, listarPlantillas, publicMessage,
  type ParametroPlantilla, type PlantillaPublica, type RespuestaInstancia,
} from '../api'

const origenes: Record<PlantillaPublica['origen'], string> = {
  catalogo: 'Catálogo',
  guardada: 'Guardada por ti',
}

const plantillas = ref<PlantillaPublica[]>([])
const cargando = ref(true)
const errorLista = ref('')
const seleccionada = ref<PlantillaPublica | null>(null)
const valores = ref<Record<string, number | string>>({})
const generando = ref(false)
const errorFormulario = ref('')
const resultado = ref<RespuestaInstancia | null>(null)
const anuncio = ref('Cargando las plantillas…')
let control: AbortController | undefined

function campo(parametro: ParametroPlantilla): string { return `parametro-${parametro.nombre}` }
function esElegida(plantilla: PlantillaPublica): boolean { return seleccionada.value?.id === plantilla.id }
function rango(parametro: ParametroPlantilla): string {
  if (parametro.valores?.length) return `Valores permitidos: ${parametro.valores.join(', ')} ${parametro.unidad}.`
  return `Entre ${parametro.minimo} y ${parametro.maximo} ${parametro.unidad}${parametro.entero ? ', entero' : ''}.`
}

async function cargar() {
  control?.abort()
  const actual = new AbortController()
  control = actual
  cargando.value = true
  errorLista.value = ''
  anuncio.value = 'Cargando las plantillas…'
  try {
    plantillas.value = await listarPlantillas(actual.signal)
    if (actual.signal.aborted) return
    anuncio.value = `${plantillas.value.length} plantillas disponibles.`
  } catch (fallo) {
    if (actual.signal.aborted) return
    errorLista.value = publicMessage(fallo instanceof Error ? fallo.message : '', 'No se pudieron cargar las plantillas.')
    anuncio.value = errorLista.value
  } finally {
    if (!actual.signal.aborted) cargando.value = false
  }
}

function elegir(plantilla: PlantillaPublica) {
  seleccionada.value = plantilla
  valores.value = Object.fromEntries(plantilla.parametros.map((parametro) => [parametro.nombre, parametro.defecto]))
  errorFormulario.value = ''
  resultado.value = null
  anuncio.value = `Plantilla elegida: ${plantilla.nombre}.`
}

async function generar() {
  const plantilla = seleccionada.value
  if (!plantilla || generando.value) return
  errorFormulario.value = ''
  resultado.value = null
  // Un campo vacío no se envía como texto: el rango lo valida el servidor (RF-4).
  const vacio = plantilla.parametros.find((parametro) => typeof valores.value[parametro.nombre] !== 'number'
    || !Number.isFinite(valores.value[parametro.nombre]))
  if (vacio) {
    errorFormulario.value = `Escribe un número para «${vacio.etiqueta}».`
    return
  }
  generando.value = true
  anuncio.value = 'Generando la pieza desde la plantilla…'
  try {
    resultado.value = await instanciarPlantilla(plantilla.id, { ...valores.value } as Record<string, number>)
    anuncio.value = 'Pieza generada desde la plantilla.'
  } catch (fallo) {
    errorFormulario.value = publicMessage(fallo instanceof Error ? fallo.message : '', 'No se pudo generar la pieza desde la plantilla.')
    anuncio.value = errorFormulario.value
  } finally {
    generando.value = false
  }
}

onMounted(cargar)
onBeforeUnmount(() => control?.abort())
</script>

<template>
  <section class="panel" aria-labelledby="plantillas-title">
    <h2 id="plantillas-title">Plantillas</h2>
    <p class="muted">Parte de una pieza frecuente y ajusta sus medidas: la pieza se genera sin el modelo.</p>
    <p class="help anuncio" aria-live="polite" role="status">{{ anuncio }}</p>
    <p v-if="errorLista" class="field-error" role="alert">
      {{ errorLista }}
      <button type="button" @click="cargar">Reintentar</button>
    </p>
    <p v-else-if="!cargando && plantillas.length === 0" class="muted">No hay plantillas disponibles.</p>
    <ul v-else class="plantillas" aria-label="Plantillas disponibles">
      <li v-for="plantilla in plantillas" :key="plantilla.id" class="plantilla" :class="{ 'plantilla--elegida': esElegida(plantilla) }" :data-test="`plantilla-${plantilla.id}`">
        <p class="plantilla-meta">
          <strong>{{ plantilla.nombre }}</strong>
          <span class="etiquetas">
            <span v-if="esElegida(plantilla)" class="elegida">Elegida</span>
            <span class="origen">{{ origenes[plantilla.origen] }}</span>
          </span>
        </p>
        <p>{{ plantilla.descripcion }}</p>
        <button
          type="button"
          :aria-pressed="esElegida(plantilla)"
          @click="elegir(plantilla)"
        >
          Usar «{{ plantilla.nombre }}»
        </button>
      </li>
    </ul>

    <p v-if="!seleccionada && !cargando && plantillas.length" class="muted ayuda">Elige una plantilla para ajustar sus medidas.</p>

    <form v-if="seleccionada" class="parametros" aria-labelledby="parametros-title" novalidate @submit.prevent="generar">
      <h3 id="parametros-title">Parámetros de {{ seleccionada.nombre }}</h3>
      <div v-for="parametro in seleccionada.parametros" :key="parametro.nombre" class="parametro">
        <label :for="campo(parametro)">{{ parametro.etiqueta }} ({{ parametro.unidad }})</label>
        <select
          v-if="parametro.valores?.length"
          :id="campo(parametro)"
          v-model.number="valores[parametro.nombre]"
          :aria-describedby="`${campo(parametro)}-rango`"
        >
          <option v-for="valor in parametro.valores" :key="valor" :value="valor">{{ valor }}</option>
        </select>
        <input
          v-else
          :id="campo(parametro)"
          v-model.number="valores[parametro.nombre]"
          type="number"
          inputmode="decimal"
          :min="parametro.minimo"
          :max="parametro.maximo"
          :step="parametro.entero ? 1 : 'any'"
          :aria-describedby="`${campo(parametro)}-rango`"
          required
        >
        <p :id="`${campo(parametro)}-rango`" class="help">{{ rango(parametro) }}</p>
      </div>
      <button class="primary" type="submit" :disabled="generando">{{ generando ? 'Generando…' : 'Generar pieza' }}</button>
      <p v-if="errorFormulario" class="field-error" role="alert" data-test="error-plantilla">{{ errorFormulario }}</p>
    </form>
    <section v-if="resultado" class="resultado" aria-labelledby="resultado-title" data-test="resultado-plantilla">
      <h3 id="resultado-title">Pieza generada</h3>
      <dl>
        <div><dt>Volumen</dt><dd data-test="volumen">{{ resultado.volumen_mm3 }} mm³</dd></div>
        <div><dt>Caja envolvente</dt><dd data-test="caja">{{ resultado.caja_mm }} mm</dd></div>
      </dl>
      <p class="help">{{ resultado.aviso }}</p>
      <RouterLink :to="`/historial/${resultado.solicitud_id}`" data-test="ver-solicitud">
        Ver la solicitud y descargar el STEP
      </RouterLink>
    </section>
  </section>
</template>

<style scoped>
.anuncio { margin-bottom: var(--space-4); }
.plantillas { display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); gap: var(--space-4); margin: 0 0 var(--space-5); padding: 0; list-style: none; }
.plantilla { display: grid; gap: var(--space-2); padding: var(--space-4); border: var(--border-width) solid var(--color-border); border-radius: var(--radius-small); background: var(--color-surface-subtle); }
.plantilla--elegida { border-color: var(--color-accent); }
.plantilla-meta { display: flex; flex-wrap: wrap; gap: var(--space-3); justify-content: space-between; margin: 0; }
.plantilla p { margin: 0; }
.etiquetas { display: inline-flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
.origen { color: var(--color-muted); font-size: var(--text-small); }
.elegida { padding: 0 var(--space-2); border-radius: var(--radius-small); background: var(--color-accent); color: var(--color-on-accent); font-size: var(--text-small); font-weight: var(--weight-strong); }
/* El estado presionado debe seguir siendo legible: fondo y texto del par accent/on-accent. */
.plantilla button[aria-pressed='true'] { border-color: var(--color-accent); background: var(--color-accent); color: var(--color-on-accent); }
.plantilla button { justify-self: start; }
.ayuda { margin-bottom: var(--space-4); }
.parametros { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: var(--space-3); align-items: start; margin-bottom: var(--space-5); padding: var(--space-4); border: var(--border-width) solid var(--color-border); border-radius: var(--radius-small); background: var(--color-surface-subtle); }
.parametros h3, .parametros > button, .parametros .field-error { grid-column: 1 / -1; }
.parametros > button { justify-self: start; }
.parametro p { margin: var(--space-1) 0 0; }
select { width: 100%; min-height: var(--control-min); padding: var(--space-2) var(--space-3); border: var(--border-width) solid var(--color-border); border-radius: var(--radius-small); color: var(--color-text); background: var(--color-surface); font: inherit; }
.resultado { margin-bottom: var(--space-5); padding: var(--space-4); border: var(--border-width) solid var(--color-accent); border-radius: var(--radius-small); background: var(--color-surface-subtle); }
.resultado dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: var(--space-3); margin: 0 0 var(--space-3); }
.resultado dl > div { padding: var(--space-3); border: var(--border-width) solid var(--color-border); border-radius: var(--radius-small); background: var(--color-surface-subtle); }
.resultado dt { color: var(--color-muted); font-size: var(--text-small); }
.resultado dd { margin: var(--space-1) 0 0; font: var(--weight-strong) var(--text-body)/var(--line-body) var(--font-technical); }
</style>
