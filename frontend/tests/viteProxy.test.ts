import { describe, expect, it } from 'vitest'
import config from '../vite.config'

describe('proxy de desarrollo y preview (HU-31)', () => {
  it('envía sólo el prefijo /v1 al backend', () => {
    const servidor = config.server as { proxy: Record<string, unknown> } | undefined
    const proxy = servidor?.proxy

    expect(Object.keys(proxy ?? {})).toEqual(['/v1'])
    expect(proxy?.['/v1']).toBe('http://127.0.0.1:8000')
  })
})
