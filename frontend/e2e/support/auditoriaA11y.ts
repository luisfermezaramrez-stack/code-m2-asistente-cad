import { expect, type Page } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'

type Impacto = 'critical' | 'serious' | 'moderate' | 'minor' | null

interface Violacion {
  id: string
  impact: Impacto
  help: string
  nodes: Array<{ target: string[]; failureSummary?: string }>
}

interface ResultadoAxe {
  violations: Violacion[]
}

interface VentanaConAxe extends Window {
  axe?: {
    run(context: Document, options: unknown): Promise<ResultadoAxe>
  }
}

const require = createRequire(import.meta.url)
const fuenteAxe = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8')

function detalle(violaciones: Violacion[]): string {
  return violaciones.map((violacion) => [
    `- ${violacion.id} (${violacion.impact}): ${violacion.help}`,
    ...violacion.nodes.map((nodo) => `  ${nodo.target.join(' ')}: ${nodo.failureSummary ?? ''}`),
  ].join('\n')).join('\n')
}

export async function auditarAccesibilidad(page: Page, vista: string): Promise<void> {
  await page.addScriptTag({ content: fuenteAxe })
  const resultado = await page.evaluate(async (): Promise<ResultadoAxe> => {
    const axe = (window as VentanaConAxe).axe
    if (!axe) throw new Error('axe-core no se inyectó en la página.')
    return axe.run(document, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
      rules: { 'color-contrast': { enabled: true } },
    })
  })

  const graves = resultado.violations.filter((violacion) => (
    violacion.impact === 'critical' || violacion.impact === 'serious'
  ))
  expect(graves, `${vista}: violaciones axe críticas o serias\n${detalle(graves)}`).toEqual([])

  const contraste = resultado.violations.filter((violacion) => violacion.id === 'color-contrast')
  expect(contraste, `${vista}: contraste WCAG AA\n${detalle(contraste)}`).toEqual([])
}
