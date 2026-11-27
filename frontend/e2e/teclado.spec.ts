import { expect, test, type Locator, type Page } from '@playwright/test'
import { DESCRIPCION } from './support/acciones'
import { event, servirBackend } from './support/fakeCadService'

async function tabHasta(page: Page, selector: string): Promise<Locator> {
  for (let intento = 0; intento < 30; intento++) {
    const objetivo = page.locator(selector)
    if (await objetivo.evaluate((elemento) => elemento === document.activeElement)) return objetivo
    await page.keyboard.press('Tab')
  }
  throw new Error(`No se alcanzó ${selector} usando sólo Tab.`)
}

async function foco(page: Page): Promise<string> {
  return page.evaluate(() => {
    const activo = document.activeElement
    if (!activo) return ''
    return [activo.tagName.toLowerCase(), activo.id, activo.className].filter(Boolean).join(':')
  })
}

test.describe('flujo sin mouse', () => {
  test('se completa con teclado y mantiene el foco durante el progreso', async ({ page }) => {
    await servirBackend(page, {
      frames: [
        event('validando', 1),
        event('generando', 2),
        event('verificado', 3, { resultado: { step: 'pieza.step', bom_csv: 'bom.csv' } }),
      ],
      archivos: ['step', 'csv'],
    })
    await page.goto('/')

    const salto = await tabHasta(page, 'a.skip')
    await expect(salto).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(page.locator('main#contenido')).toBeFocused()

    const tema = await tabHasta(page, 'button.theme-toggle')
    await page.keyboard.press('Enter')
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    await expect(tema).toHaveText('Usar tema claro')

    const descripcion = await tabHasta(page, '#descripcion')
    expect(await descripcion.evaluate((elemento) => getComputedStyle(elemento).outlineWidth)).toBe('3px')
    await page.keyboard.insertText(DESCRIPCION)

    const generar = await tabHasta(page, 'button[type="submit"]')
    await expect(generar).toBeFocused()
    await page.keyboard.press('Enter')

    await expect(page.locator('ol.steps')).toHaveAttribute('aria-live', 'polite')
    await expect(generar).toBeFocused()
    const focoAntes = await foco(page)
    await expect(page.locator('ol.steps li')).toHaveText([
      'Validando solicitud',
      'Generando pieza',
      'Pieza verificada',
    ])
    await expect(page.locator('.state')).toHaveClass(/verificado/)
    expect(await foco(page)).toBe(focoAntes)

    await tabHasta(page, '[data-download-filename="pieza.step"]')
    const descargaPrometida = page.waitForEvent('download')
    await page.keyboard.press('Enter')
    expect((await descargaPrometida).suggestedFilename()).toBe('pieza.step')
  })
})
