import { expect, test, type Page } from '@playwright/test'
import { DESCRIPCION } from './support/acciones'
import { auditarAccesibilidad } from './support/auditoriaA11y'
import { event, servirBackend } from './support/fakeCadService'

type Tema = 'light' | 'dark'

const resultado = { step: 'pieza.step', glb: 'pieza.glb', bom_csv: 'bom.csv' }

async function fijarTema(page: Page, tema: Tema): Promise<void> {
  await page.goto('/')
  await page.evaluate((valor) => window.localStorage.setItem('m2-cad-theme', valor), tema)
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', tema)
}

test.describe('auditoría axe WCAG 2.1 AA', () => {
  for (const tema of ['light', 'dark'] as const) {
    test(`sin violaciones críticas ni serias en ${tema}`, async ({ page }) => {
      await servirBackend(page, {
        frames: [
          event('validando', 1),
          event('generando', 2),
          event('verificado', 3, { resultado }),
        ],
        archivos: ['step', 'csv'],
      })
      await fijarTema(page, tema)

      for (const vista of [
        { nombre: 'nueva solicitud', ruta: '/nueva-solicitud' },
        { nombre: 'historial', ruta: '/historial' },
      ]) {
        await test.step(vista.nombre, async () => {
          await page.goto(vista.ruta)
          await expect(page.locator('header .theme-toggle')).toBeVisible()
          await auditarAccesibilidad(page, `${vista.nombre} (${tema})`)
        })
      }

      await test.step('resultado', async () => {
        await page.goto('/nueva-solicitud')
        await page.locator('#descripcion').fill(DESCRIPCION)
        await page.getByRole('button', { name: 'Generar pieza' }).click()
        await expect(page.locator('.state')).toHaveClass(/verificado/)
        await expect(page.locator('button.download')).toHaveCount(2)
        await auditarAccesibilidad(page, `resultado (${tema})`)
      })
    })
  }
})
