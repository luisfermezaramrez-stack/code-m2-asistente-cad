import { computed, onScopeDispose, ref } from 'vue'
import { availableArtifacts, parseJob, publicMessage, requestJob, type Artifact, type Job, type Stage } from './api'
import { readSSE } from './sse'

export function useGeneration() {
  const description = ref('')
  const timeoutSeconds = ref(180)
  const job = ref<Job | null>(null)
  const requestId = ref('')
  const stages = ref<Stage[]>([])
  const artifacts = ref<Artifact[]>([])
  const busy = ref(false)
  const checking = ref(false)
  const cancelling = ref(false)
  const loadingFiles = ref(false)
  const message = ref('')
  const inputError = ref('')
  const filesError = ref('')
  const disconnected = ref(false)
  const canCancel = computed(() => (busy.value || !!requestId.value)
    && !job.value?.terminal && !job.value?.cancelacion_solicitada && !cancelling.value)
  const canCheck = computed(() => !!requestId.value && !job.value?.terminal)
  let epoch = 0
  let streamController: AbortController | undefined
  const controllers = new Set<AbortController>()
  const isFinished = () => !!job.value?.terminal

  function abortAll() {
    for (const controller of controllers) controller.abort()
    controllers.clear()
  }

  function controller() {
    const value = new AbortController()
    controllers.add(value)
    return value
  }

  async function applyJob(incoming: Job, current: number) {
    if (current !== epoch) return
    if (requestId.value && incoming.solicitud_id !== requestId.value) throw new Error('Identificador incorrecto.')
    if (job.value?.terminal) return
    if ((incoming.secuencia ?? 0) < (job.value?.secuencia ?? 0)) return
    requestId.value = incoming.solicitud_id
    incoming = { ...incoming, cancelacion_solicitada: incoming.cancelacion_solicitada || !!job.value?.cancelacion_solicitada }
    job.value = incoming
    if (incoming.estado !== 'iniciando' && !stages.value.includes(incoming.estado)) stages.value.push(incoming.estado)
    if (!incoming.terminal) return
    disconnected.value = false
    artifacts.value = []
    if (incoming.estado === 'declinado') message.value = publicMessage(incoming.motivo, 'La pieza está fuera del catálogo admitido.')
    if (incoming.estado === 'error') message.value = publicMessage(incoming.motivo, 'No se pudo completar la solicitud. Vuelve a intentarlo.')
    if (incoming.estado === 'cancelado') message.value = 'El procesamiento local se detuvo en un punto seguro. No se confirma la detención de servicios remotos.'
    if (incoming.estado === 'verificado' && incoming.resultado) {
      message.value = 'Verificación geométrica completada.'
      loadingFiles.value = true
      const filesController = controller()
      const filesTimer = setTimeout(() => filesController.abort(), 10_000)
      try {
        const found = await availableArtifacts(incoming.solicitud_id, incoming.resultado, filesController.signal)
        if (current === epoch) artifacts.value = found
      } catch {
        if (current === epoch) filesError.value = 'No se pudo comprobar la disponibilidad de los archivos.'
      } finally {
        clearTimeout(filesTimer)
        controllers.delete(filesController)
        if (current === epoch) loadingFiles.value = false
      }
    }
  }

  async function refresh() {
    if (!requestId.value || checking.value || job.value?.terminal) return
    const current = epoch
    const control = controller()
    checking.value = true
    const timer = setTimeout(() => control.abort(), 10_000)
    try {
      await applyJob(await requestJob(requestId.value, 'GET', control.signal), current)
    } catch (error) {
      if (current === epoch) message.value = publicMessage(error instanceof Error ? error.message : '', 'No se pudo consultar el estado. Vuelve a intentarlo.')
    } finally {
      clearTimeout(timer)
      controllers.delete(control)
      if (current === epoch) checking.value = false
    }
  }

  function stopWaiting() {
    streamController?.abort()
  }

  async function cancel() {
    if (!canCancel.value) return
    if (!requestId.value) { stopWaiting(); return }
    const current = epoch
    const control = controller()
    cancelling.value = true
    const timer = setTimeout(() => control.abort(), 10_000)
    try {
      await applyJob(await requestJob(requestId.value, 'DELETE', control.signal), current)
      // 202 no es un terminal: mantener el stream para recibir la salida real.
    } catch {
      if (current === epoch) message.value = 'No se pudo confirmar la solicitud de cancelación. Puedes reintentar o consultar el estado.'
    } finally {
      clearTimeout(timer)
      controllers.delete(control)
      if (current === epoch) cancelling.value = false
    }
  }

  async function start() {
    if (busy.value) return
    const text = description.value.trim()
    inputError.value = ''
    if (!text || description.value.length > 1000) {
      inputError.value = 'Escribe una descripción de entre 1 y 1000 caracteres.'
      return
    }
    if (!Number.isFinite(timeoutSeconds.value) || timeoutSeconds.value < 5 || timeoutSeconds.value > 600) {
      inputError.value = 'El tiempo de espera debe estar entre 5 y 600 segundos.'
      return
    }
    ++epoch
    const current = epoch
    abortAll()
    job.value = null; requestId.value = ''; stages.value = []; artifacts.value = []
    message.value = ''; filesError.value = ''; disconnected.value = false
    loadingFiles.value = false; checking.value = false; cancelling.value = false; busy.value = true
    const control = controller()
    streamController = control
    let timedOut = false
    let streamOpened = false
    const timer = setTimeout(() => { timedOut = true; control.abort() }, timeoutSeconds.value * 1000)
    try {
      const response = await fetch('/generar', {
        method: 'POST', signal: control.signal,
        headers: { Accept: 'text/event-stream', 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: text }),
      })
      if (current !== epoch) return
      const id = response.headers.get('X-Solicitud-ID')
      if (id && /^[a-zA-Z0-9_-]{1,128}$/.test(id)) requestId.value = id
      if (!response.ok) {
        const fallback = response.status === 422 ? 'Solicitud inválida. Revisa la descripción.' : 'El servicio no está disponible. Vuelve a intentarlo.'
        const data: unknown = await response.json().catch(() => null)
        const detail = typeof data === 'object' && data !== null && 'detail' in data ? data.detail : null
        const errorMessage = publicMessage(detail, fallback)
        if (response.status === 422) inputError.value = errorMessage
        throw new Error(errorMessage)
      }
      if (!response.headers.get('Content-Type')?.startsWith('text/event-stream') || !response.body) {
        throw new Error('El servicio no informa progreso para esta solicitud.')
      }
      let sequence = 0
      streamOpened = true
      let previous: Stage | undefined
      for await (const frame of readSSE(response.body)) {
        if (current !== epoch) break
        const incoming = parseJob(JSON.parse(frame.data))
        if (frame.event !== incoming.estado || incoming.secuencia !== sequence + 1
          || (frame.id && frame.id !== `${incoming.solicitud_id}:${incoming.secuencia}`)
          || incoming.estado === 'iniciando'
          || (incoming.estado === 'validando' && previous !== undefined)
          || (incoming.estado === 'generando' && previous !== 'validando')) throw new Error('El servicio devolvió un progreso inválido.')
        sequence = incoming.secuencia
        previous = incoming.estado
        await applyJob(incoming, current)
        if (incoming.terminal) break
      }
      if (current === epoch && !isFinished()) throw new Error('Se interrumpió la conexión antes del resultado.')
    } catch (error) {
      if (current !== epoch || isFinished()) return
      disconnected.value = true
      message.value = timedOut
        ? 'Se agotó el tiempo de espera. No se ha confirmado que el procesamiento se detuviera.'
        : control.signal.aborted
          ? 'Se interrumpió la espera. No se ha confirmado que el procesamiento se detuviera.'
          : error instanceof SyntaxError
            ? 'No se pudo interpretar la respuesta del servicio.'
            : publicMessage(error instanceof Error ? error.message : '', 'Se perdió la conexión.')
      if (streamOpened) message.value += ' La desconexión solicita cancelación local al servidor; falta confirmar su recepción y detención en un punto seguro. No se confirma la detención de servicios remotos. Consulta el estado.'
      if (requestId.value) await refresh()
    } finally {
      clearTimeout(timer)
      controllers.delete(control)
      if (current === epoch) busy.value = false
    }
  }

  onScopeDispose(() => { ++epoch; abortAll() })
  return { description, timeoutSeconds, job, stages, artifacts, busy, checking, cancelling,
    loadingFiles, message, inputError, filesError, disconnected, canCancel, canCheck,
    start, cancel, refresh, stopWaiting }
}
