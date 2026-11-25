import { afterEach, describe, expect, it, vi } from 'vitest'
import { cerrarSesion, estadoSesion, iniciarSesion, sinSesion } from '../src/auth'

afterEach(() => vi.unstubAllGlobals())

describe('sesión HU-53', () => {
  it('lee el estado público de la API', async () => {
    const fetch = vi.fn(async () => Response.json({ requerido: true, autenticado: false, usuario: null }))
    vi.stubGlobal('fetch', fetch)

    expect(await estadoSesion()).toEqual({ requerido: true, autenticado: false, usuario: null })
    expect(fetch).toHaveBeenCalledWith('/auth/me', { credentials: 'same-origin' })
  })

  it('devuelve modo local si no hay servicio de autenticación', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('sin red') }))
    expect(await estadoSesion()).toEqual(sinSesion)
  })

  it('envía credenciales sin guardar la clave en el cliente', async () => {
    const fetch = vi.fn(async () => Response.json({ autenticado: true, usuario: 'ana' }))
    vi.stubGlobal('fetch', fetch)

    expect(await iniciarSesion('ana', 'clave-secreta')).toEqual({ autenticado: true, usuario: 'ana' })
    const llamada = fetch.mock.calls[0] as unknown as [string, RequestInit]
    expect(llamada[0]).toBe('/auth/login')
    expect(JSON.parse(String(llamada[1].body))).toEqual({ usuario: 'ana', clave: 'clave-secreta' })
    expect(String(llamada[1].body)).not.toContain('localStorage')
  })

  it('muestra un mensaje público ante credenciales inválidas', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 401 })))
    await expect(iniciarSesion('ana', 'mala')).rejects.toThrow('Usuario o clave incorrectos.')
  })

  it('cierra la sesión con POST', async () => {
    const fetch = vi.fn(async () => Response.json({ autenticado: false }))
    vi.stubGlobal('fetch', fetch)
    await cerrarSesion()
    expect(fetch).toHaveBeenCalledWith('/auth/logout', {
      method: 'POST',
      credentials: 'same-origin',
    })
  })
})
