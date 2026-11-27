<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { cerrarSesion, estadoSesion, iniciarSesion, sinSesion, type EstadoSesion } from './auth'
import { activeTheme, initTheme, setTheme, type Theme } from './design/theme'
import { provideGeneration } from './useGeneration'

const router = useRouter()
// La generación pertenece al shell: sobrevive a la navegación entre vistas.
provideGeneration()
const nav = ref<HTMLElement | null>(null)
const sesion = ref<EstadoSesion>(sinSesion)
const cargandoSesion = ref(true)
const usuarioSesion = ref('')
const claveSesion = ref('')
const errorSesion = ref('')
const entrando = ref(false)
const necesitaLogin = computed(() => sesion.value.requerido && !sesion.value.autenticado)
const themeLabel = computed(() => activeTheme.value === 'dark' ? 'Usar tema claro' : 'Usar tema oscuro')
let stopTheme: (() => void) | undefined

onMounted(() => { stopTheme = initTheme() })
onBeforeUnmount(() => stopTheme?.())

function toggleTheme() {
  const next: Theme = activeTheme.value === 'dark' ? 'light' : 'dark'
  setTheme(next)
}

function manejarTeclado(event: KeyboardEvent) {
  const enlaces = Array.from(nav.value?.querySelectorAll<HTMLAnchorElement>('a[href]') ?? [])
  const indice = enlaces.indexOf(document.activeElement as HTMLAnchorElement)
  if (indice < 0) return

  if (event.key === 'Enter') {
    event.preventDefault()
    const enlace = enlaces[indice]
    if (!enlace) return
    const destino = enlace.getAttribute('href')
    if (destino) void router.push(destino)
    return
  }

  if (event.key !== 'Tab') return
  const siguiente = event.shiftKey ? indice - 1 : indice + 1
  const destino = enlaces[siguiente]
  if (!destino) return
  event.preventDefault()
  destino.focus()
}

onMounted(async () => {
  sesion.value = await estadoSesion()
  cargandoSesion.value = false
})

async function entrar() {
  errorSesion.value = ''
  entrando.value = true
  try {
    await iniciarSesion(usuarioSesion.value, claveSesion.value)
    sesion.value = await estadoSesion()
    claveSesion.value = ''
  } catch (error) {
    errorSesion.value = error instanceof Error ? error.message : 'No se pudo iniciar sesión.'
  } finally {
    entrando.value = false
  }
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
  usuarioSesion.value = ''
}
</script>

<template>
  <a class="skip" href="#contenido">Saltar al contenido</a>
  <div class="shell">
    <header class="masthead">
      <div>
        <p class="brand">M2 / ASISTENTE CAD</p>
        <h1>De la descripción a la pieza</h1>
        <p class="muted">Componentes metálicos auxiliares · Solicitudes en español</p>
      </div>
      <button class="theme-toggle" type="button" :aria-label="themeLabel" @click="toggleTheme">{{ themeLabel }}</button>
    </header>
    <aside class="notice" aria-label="Aviso profesional"><strong>Diseño preliminar: requiere revisión profesional</strong><br>La verificación geométrica no certifica resistencia ni cumplimiento normativo.</aside>
    <nav ref="nav" class="nav" aria-label="Navegación principal" @keydown="manejarTeclado">
      <RouterLink to="/nueva-solicitud">Nueva solicitud</RouterLink>
      <RouterLink to="/historial">Historial</RouterLink>
      <RouterLink to="/ajustes">Ajustes</RouterLink>
    </nav>
    <section v-if="sesion.requerido && !cargandoSesion" class="panel sesion" aria-labelledby="sesion-title">
      <h2 id="sesion-title">Acceso al servicio</h2>
      <form v-if="!sesion.autenticado" class="sesion-form" @submit.prevent="entrar">
        <label for="usuario">Usuario</label>
        <input id="usuario" v-model="usuarioSesion" autocomplete="username" required>
        <label for="clave">Clave</label>
        <input id="clave" v-model="claveSesion" type="password" autocomplete="current-password" required>
        <button class="primary" type="submit" :disabled="entrando">{{ entrando ? 'Entrando…' : 'Iniciar sesión' }}</button>
      </form>
      <p v-else>Generando como <strong>{{ sesion.usuario }}</strong>. <button type="button" @click="salir">Cerrar sesión</button></p>
      <p v-if="errorSesion" class="field-error" role="alert">{{ errorSesion }}</p>
    </section>
    <main id="contenido" class="view">
      <RouterView v-slot="{ Component, route }">
        <component :is="Component" v-bind="route.name === 'nueva-solicitud' ? { necesitaLogin } : {}" />
      </RouterView>
    </main>
  </div>
</template>

<style scoped>
.sesion { margin-bottom: 1rem; }
.sesion-form { display: grid; gap: .5rem; max-width: 24rem; }
</style>
