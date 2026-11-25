/** Sesión HU-53: la cookie HttpOnly la gestiona el navegador, nunca localStorage. */

export interface EstadoSesion {
  requerido: boolean
  autenticado: boolean
  usuario: string | null
}

export interface RespuestaLogin {
  autenticado: boolean
  usuario: string
}

export const sinSesion: EstadoSesion = { requerido: false, autenticado: false, usuario: null }

async function leerJson<T>(url: string, init?: RequestInit): Promise<T> {
  const respuesta = await fetch(url, { ...init, credentials: 'same-origin' })
  if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`)
  return (await respuesta.json()) as T
}

export async function estadoSesion(): Promise<EstadoSesion> {
  try {
    return await leerJson<EstadoSesion>('/auth/me')
  } catch {
    return sinSesion
  }
}

export async function iniciarSesion(usuario: string, clave: string): Promise<RespuestaLogin> {
  const respuesta = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({ usuario, clave }),
  })
  if (respuesta.status === 401) throw new Error('Usuario o clave incorrectos.')
  if (!respuesta.ok) throw new Error('No se pudo iniciar sesión. Vuelve a intentarlo.')
  return (await respuesta.json()) as RespuestaLogin
}

export async function cerrarSesion(): Promise<void> {
  await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' })
}
