<script setup lang="ts">
import { computed } from 'vue'
import { activeTheme, setTheme, type Theme } from '../design/theme'

const oscuro = computed(() => activeTheme.value === 'dark')
// El nombre accesible describe la acción, no el icono: el icono es decorativo.
const etiqueta = computed(() => (oscuro.value ? 'Usar tema claro' : 'Usar tema oscuro'))

function alternar() {
  const siguiente: Theme = oscuro.value ? 'light' : 'dark'
  setTheme(siguiente)
}
</script>

<template>
  <button class="theme-toggle" type="button" :aria-label="etiqueta" :title="etiqueta" @click="alternar">
    <svg v-if="oscuro" class="theme-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" />
    </svg>
    <svg v-else class="theme-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.6 6.6 0 0 0 9.8 9.8z" />
    </svg>
  </button>
</template>
