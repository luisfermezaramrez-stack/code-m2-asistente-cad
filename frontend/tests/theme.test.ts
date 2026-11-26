import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { activeTheme, clearThemePreference, initTheme, setTheme, THEME_STORAGE_KEY } from '../src/design/theme'

type Listener = (event: MediaQueryListEvent) => void

let dispose: (() => void) | undefined

function installMatchMedia(initial: boolean) {
  const listeners = new Set<Listener>()
  const media = {
    matches: initial,
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addEventListener: (_type: string, listener: Listener) => listeners.add(listener),
    removeEventListener: (_type: string, listener: Listener) => listeners.delete(listener),
    addListener: (listener: Listener) => listeners.add(listener),
    removeListener: (listener: Listener) => listeners.delete(listener),
    dispatchEvent: () => true,
  }
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn(() => media),
  })
  return {
    change(next: boolean) {
      media.matches = next
      const event = { matches: next, media: media.media } as MediaQueryListEvent
      for (const listener of [...listeners]) listener(event)
    },
  }
}

describe('preferencia de tema', () => {
  beforeEach(() => {
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  afterEach(() => {
    dispose?.()
    dispose = undefined
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    Reflect.deleteProperty(window, 'matchMedia')
  })

  it('usa el tema oscuro del sistema sin preferencia guardada', () => {
    installMatchMedia(true)

    dispose = initTheme()

    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(activeTheme.value).toBe('dark')
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull()
  })

  it('respeta la preferencia explícita aunque el sistema prefiera oscuro', () => {
    installMatchMedia(true)
    window.localStorage.setItem(THEME_STORAGE_KEY, 'light')

    dispose = initTheme()

    expect(document.documentElement.dataset.theme).toBe('light')
    expect(activeTheme.value).toBe('light')
  })

  it('persiste la elección del usuario y la devuelve al sistema al borrarla', () => {
    const system = installMatchMedia(true)
    dispose = initTheme()

    setTheme('light')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('light')

    system.change(false)
    expect(document.documentElement.dataset.theme).toBe('light')

    clearThemePreference()
    expect(document.documentElement.dataset.theme).toBe('light')

    system.change(true)
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('sigue los cambios del sistema mientras no haya preferencia guardada', () => {
    const system = installMatchMedia(false)
    dispose = initTheme()
    expect(document.documentElement.dataset.theme).toBe('light')

    system.change(true)
    expect(document.documentElement.dataset.theme).toBe('dark')

    system.change(false)
    expect(document.documentElement.dataset.theme).toBe('light')
  })
})
