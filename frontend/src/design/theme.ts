import { ref } from 'vue'

export type Theme = 'light' | 'dark'

export const THEME_STORAGE_KEY = 'm2-cad-theme'
export const activeTheme = ref<Theme>('light')

const darkQuery = '(prefers-color-scheme: dark)'
let disposeSystemWatch: (() => void) | undefined

function storedTheme(): Theme | null {
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

function systemDark(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia(darkQuery).matches
}

function resolvedTheme(): Theme {
  return storedTheme() ?? (systemDark() ? 'dark' : 'light')
}

function applyTheme(theme: Theme): void {
  activeTheme.value = theme
  if (typeof document !== 'undefined') document.documentElement.dataset.theme = theme
}

export function initTheme(): () => void {
  applyTheme(resolvedTheme())
  if (disposeSystemWatch) return disposeSystemWatch
  if (typeof window.matchMedia !== 'function') return () => {}

  const media = window.matchMedia(darkQuery)
  const onChange = () => {
    if (storedTheme() === null) applyTheme(systemDark() ? 'dark' : 'light')
  }
  if (typeof media.addEventListener === 'function') media.addEventListener('change', onChange)
  else media.addListener(onChange)

  disposeSystemWatch = () => {
    if (typeof media.removeEventListener === 'function') {
      media.removeEventListener('change', onChange)
    } else {
      media.removeListener(onChange)
    }
    disposeSystemWatch = undefined
  }
  return disposeSystemWatch
}

export function setTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {}
  applyTheme(theme)
}

export function clearThemePreference(): void {
  try {
    window.localStorage.removeItem(THEME_STORAGE_KEY)
  } catch {}
  applyTheme(resolvedTheme())
}
