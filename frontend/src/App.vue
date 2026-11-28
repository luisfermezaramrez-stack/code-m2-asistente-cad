<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { cerrarSesion, estadoSesion, sinSesion, type EstadoSesion, type RespuestaLogin } from './auth'
import BotonTema from './components/BotonTema.vue'
import { initTheme } from './design/theme'
import { provideGeneration } from './useGeneration'
import LoginView from './views/LoginView.vue'

// La generación pertenece al shell: sobrevive a la navegación entre vistas.
provideGeneration()
const sesion = ref<EstadoSesion>(sinSesion)
const cargandoSesion = ref(true)
const errorSesion = ref('')
let stopTheme: (() => void) | undefined

// El acceso ocupa la pantalla completa: nada de la aplicación se dibuja antes de entrar.
const estadoAcceso = computed<'cargando' | 'acceso' | 'app'>(() => {
  if (cargandoSesion.value) return 'cargando'
  return sesion.value.requerido && !sesion.value.autenticado ? 'acceso' : 'app'
})

onMounted(() => { stopTheme = initTheme() })
onBeforeUnmount(() => stopTheme?.())

onMounted(async () => {
  sesion.value = await estadoSesion()
  cargandoSesion.value = false
})

// El formulario de acceso vive en su propia pantalla y avisa cuando la sesión existe.
function alEntrar(respuesta: RespuestaLogin) {
  errorSesion.value = ''
  sesion.value = { requerido: true, autenticado: respuesta.autenticado, usuario: respuesta.usuario }
}

async function salir() {
  errorSesion.value = ''
  try {
    await cerrarSesion()
  } catch {
    errorSesion.value = 'No se pudo cerrar la sesión. Vuelve a intentarlo.'
    return
  }
  sesion.value = await estadoSesion()
}
</script>

<template>
  <div v-if="estadoAcceso === 'cargando'" class="acceso">
    <div class="acceso-cabecera">
      <p class="brand">M2 / ASISTENTE CAD</p>
      <BotonTema />
    </div>
    <p role="status">Comprobando la sesión…</p>
  </div>
  <LoginView v-else-if="estadoAcceso === 'acceso'" @entrado="alEntrar" />
  <template v-else>
    <a class="skip" href="#contenido">Saltar al contenido</a>
    <div class="shell">
      <header class="masthead">
        <div>
          <p class="brand">M2 / ASISTENTE CAD</p>
          <h1>De la descripción a la pieza</h1>
          <p class="muted">Componentes metálicos auxiliares · Solicitudes en español</p>
        </div>
        <div class="masthead-acciones">
          <p v-if="sesion.autenticado" class="sesion-usuario">Generando como <strong>{{ sesion.usuario }}</strong>. <button type="button" @click="salir">Cerrar sesión</button></p>
          <BotonTema />
        </div>
      </header>
      <p v-if="errorSesion" class="field-error" role="alert">{{ errorSesion }}</p>
      <aside class="notice" aria-label="Aviso profesional"><strong>Diseño preliminar: requiere revisión profesional</strong><br>La verificación geométrica no certifica resistencia ni cumplimiento normativo.</aside>
      <nav class="nav" aria-label="Navegación principal">
        <RouterLink to="/nueva-solicitud">Nueva solicitud</RouterLink>
        <RouterLink to="/historial">Historial</RouterLink>
        <RouterLink to="/plantillas">Plantillas</RouterLink>
      </nav>
      <main id="contenido" class="view" tabindex="-1">
        <RouterView />
      </main>
    </div>
  </template>
</template>
