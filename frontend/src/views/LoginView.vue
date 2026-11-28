<script setup lang="ts">
import { ref } from 'vue'
import { iniciarSesion, type RespuestaLogin } from '../auth'
import BotonTema from '../components/BotonTema.vue'

const emit = defineEmits<{ entrado: [respuesta: RespuestaLogin] }>()

const usuario = ref('')
const clave = ref('')
const error = ref('')
const entrando = ref(false)

async function enviar() {
  error.value = ''
  entrando.value = true
  try {
    const respuesta = await iniciarSesion(usuario.value, clave.value)
    clave.value = ''
    emit('entrado', respuesta)
  } catch (fallo) {
    error.value = fallo instanceof Error ? fallo.message : 'No se pudo iniciar sesión.'
  } finally {
    entrando.value = false
  }
}
</script>

<template>
  <div class="acceso">
    <div class="acceso-cabecera">
      <p class="brand">M2 / ASISTENTE CAD</p>
      <BotonTema />
    </div>
    <section class="panel" aria-labelledby="acceso-title">
      <h1 id="acceso-title">De la descripción a la pieza</h1>
      <p class="muted">Acceso al servicio · Componentes metálicos auxiliares</p>
      <form class="acceso-form" novalidate @submit.prevent="enviar">
        <label for="usuario">Usuario</label>
        <input id="usuario" v-model="usuario" autocomplete="username" required>
        <label for="clave">Clave</label>
        <input id="clave" v-model="clave" type="password" autocomplete="current-password" required>
        <button class="primary" type="submit" :disabled="entrando">{{ entrando ? 'Entrando…' : 'Iniciar sesión' }}</button>
      </form>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
    </section>
  </div>
</template>
