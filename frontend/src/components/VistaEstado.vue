<script setup lang="ts">
import type { EstadoVista } from '../estadosVista'

const props = defineProps<{ estado: EstadoVista; textos: Record<EstadoVista, string> }>()
</script>

<template>
  <div
    class="state estado-vista"
    :class="`estado-vista--${estado}`"
    :role="estado === 'error' ? 'alert' : 'status'"
    :aria-busy="estado === 'cargando'"
  >
    <strong>{{ props.textos[props.estado] }}</strong>
  </div>
</template>
