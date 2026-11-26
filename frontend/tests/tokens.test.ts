import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

type Palette = Record<string, string>

function source(relativePath: string): string {
  return readFileSync(new URL(relativePath, import.meta.url), 'utf8')
}

const tokensCss = source('../src/design/tokens.css')
const styleSource = source('../src/style.css')
const appSource = source('../src/App.vue')

function declarations(block: string): Palette {
  const result: Palette = {}
  for (const line of block.split('\n')) {
    const match = /^\s*(--[\w-]+):\s*([^;]+);/.exec(line)
    if (match?.[1] && match[2]) result[match[1]] = match[2].trim()
  }
  return result
}

function block(pattern: RegExp): string {
  return pattern.exec(tokensCss)?.[1] ?? ''
}

const light = declarations(block(/:root\s*\{([\s\S]*?)\n\}/))
const systemDark = declarations(block(/@media \(prefers-color-scheme: dark\)\s*\{[\s\S]*?:root:not\(\[data-theme\]\)\s*\{([\s\S]*?)\n\s*\}/))
const explicitDark = declarations(block(/:root\[data-theme='dark'\]\s*\{([\s\S]*?)\n\}/))

function luminance(hex: string): number {
  const value = hex.replace('#', '')
  if (!/^[0-9a-f]{6}$/i.test(value)) throw new Error(`Color no hexadecimal: ${hex}`)
  const channels = [0, 2, 4].map((start) => Number.parseInt(value.slice(start, start + 2), 16) / 255)
  const linear = channels.map((channel) => channel <= 0.04045
    ? channel / 12.92
    : ((channel + 0.055) / 1.055) ** 2.4)
  return 0.2126 * linear[0]! + 0.7152 * linear[1]! + 0.0722 * linear[2]!
}

function contrast(foreground: string, background: string): number {
  const first = luminance(foreground)
  const second = luminance(background)
  const lighter = Math.max(first, second)
  const darker = Math.min(first, second)
  return (lighter + 0.05) / (darker + 0.05)
}

function colorOf(palette: Palette, token: string): string {
  if (!token.startsWith('--')) return token
  const value = palette[token]
  if (!value) throw new Error(`Token ausente: ${token}`)
  return value
}

const textPairs = [
  ['--color-text', '--color-background'],
  ['--color-muted', '--color-background'],
  ['--color-muted', '--color-surface'],
  ['--color-muted', '--color-surface-subtle'],
  ['--color-accent', '--color-background'],
  ['--color-accent', '--color-surface'],
  ['--color-on-accent', '--color-accent'],
  ['--color-info', '--color-info-bg'],
  ['--color-success', '--color-success-bg'],
  ['--color-warning', '--color-warning-bg'],
  ['--color-error', '--color-error-bg'],
  ['--color-idle', '--color-idle-bg'],
]

const nonTextPairs = [
  ['--color-focus', '--color-background'],
  ['--color-focus', '--color-surface'],
  ['--color-focus', '--color-surface-subtle'],
  ['--color-border', '--color-surface'],
  ['--color-viewer-background', '#d9d9d9'],
]

describe('sistema de diseño v2', () => {
  it('mantiene los mismos tokens en ambos temas', () => {
    expect(Object.keys(light).length).toBeGreaterThan(50)
    expect(Object.keys(systemDark).sort()).toEqual(Object.keys(light).sort())
    expect(Object.keys(explicitDark).sort()).toEqual(Object.keys(light).sort())
    expect(explicitDark).toEqual(systemDark)
  })

  it('documenta la escala tipográfica existente', () => {
    expect(light['--text-small']).toBe('0.875rem')
    expect(light['--text-body']).toBe('1rem')
    expect(light['--text-heading']).toBe('1.25rem')
    expect(light['--text-title']).toBe('1.75rem')
    expect(light['--line-body']).toBe('1.6')
    expect(light['--line-heading']).toBe('1.25')
    expect(light['--weight-regular']).toBe('400')
    expect(light['--weight-strong']).toBe('600')
  })

  it('no usa fuentes ni recursos remotos', () => {
    expect(tokensCss).not.toMatch(/@import|url\(/)
    expect(styleSource).not.toMatch(/#[0-9a-f]{3,8}\b/i)
    expect(appSource).not.toMatch(/#[0-9a-f]{3,8}\b/i)
  })

  it.each(['claro', 'oscuro'] as const)('cumple contraste AA en el tema %s', (theme) => {
    const palette = theme === 'claro' ? light : systemDark
    for (const [foreground, background] of textPairs) {
      expect(contrast(colorOf(palette, foreground!), colorOf(palette, background!))).toBeGreaterThanOrEqual(4.5)
    }
    for (const [foreground, background] of nonTextPairs) {
      expect(contrast(colorOf(palette, foreground!), colorOf(palette, background!))).toBeGreaterThanOrEqual(3)
    }
  })

  it('define el esquema de color de cada tema', () => {
    expect(/:root\s*\{\s*color-scheme: light;/.test(tokensCss)).toBe(true)
    expect(/@media \(prefers-color-scheme: dark\)[\s\S]*?color-scheme: dark;/.test(tokensCss)).toBe(true)
    expect(/:root\[data-theme='dark'\]\s*\{\s*color-scheme: dark;/.test(tokensCss)).toBe(true)
  })
})
