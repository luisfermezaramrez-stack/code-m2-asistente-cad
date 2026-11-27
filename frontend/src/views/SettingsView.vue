<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import VistaEstado from '../components/VistaEstado.vue'
import { estadoDesdeConsulta } from '../estadosVista'

const route = useRoute()
const estado = computed(() => estadoDesdeConsulta(route.query.estado))
const textos = {
  vacio: 'No hay ajustes adicionales para mostrar.',
  cargando: 'Cargando los ajustes…',
  error: 'No se pudieron cargar los ajustes.',
}
</script>

<template>
  <section class="panel" aria-labelledby="ajustes-title">
    <h2 id="ajustes-title">Ajustes</h2>
    <p class="help">El tema se cambia desde la cabecera y el tiempo de espera en Nueva solicitud.</p>
    <VistaEstado :estado="estado" :textos="textos" />
  </section>
</template>
