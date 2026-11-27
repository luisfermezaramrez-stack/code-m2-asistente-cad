<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import VistaEstado from '../components/VistaEstado.vue'
import { estadoDesdeConsulta } from '../estadosVista'

const route = useRoute()
const estado = computed(() => estadoDesdeConsulta(route.query.estado))
const textos = {
  vacio: 'No hay solicitudes registradas para mostrar.',
  cargando: 'Cargando el historial…',
  error: 'No se pudo cargar el historial.',
}
</script>

<template>
  <section class="panel" aria-labelledby="historial-title">
    <h2 id="historial-title">Historial</h2>
    <p class="help">El contenido de este módulo llega con la HU del historial.</p>
    <VistaEstado :estado="estado" :textos="textos" />
  </section>
</template>
