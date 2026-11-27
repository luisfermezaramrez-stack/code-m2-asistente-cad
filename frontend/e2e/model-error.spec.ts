/**
 * SPEC-042 RF-3 / AC3: error del modelo. El backend simulado informa el fallo por
 * SSE; la UI muestra el estado y el motivo público, sin filtrar secretos.
 */
import { expect, test } from '@playwright/test'
import { enviarSolicitud } from './support/acciones'
import { event, servirBackend } from './support/fakeCadService'

const MOTIVO = 'El modelo no está configurado: falta DEEPSEEK_API_KEY.'

test.describe('error del modelo', () => {
  test('muestra el fallo y su motivo sin exponer secretos', async ({ page }) => {
    await servirBackend(page, {
      frames: [event('validando', 1), event('error', 2, { motivo: MOTIVO, codigo_http: 503 })],
    })

    await enviarSolicitud(page)

    const estado = page.locator('.state')
    await expect(estado).toHaveClass(/error/)
    await expect(estado).toContainText('No se pudo completar')
    await expect(estado).toContainText(MOTIVO)

    await expect(page.locator('.steps li')).toHaveText(['Validando solicitud', 'No se pudo completar'])
    await expect(page.locator('button.download')).toHaveCount(0)
    await expect(page.getByText('No hay archivos disponibles.')).toBeVisible()

    // RNF-1 y contrato público: ni claves, ni URLs del modelo, ni trazas.
    const texto = await page.locator('body').innerText()
    expect(texto).not.toMatch(/sk-[A-Za-z0-9]|bearer|https?:\/\/|localhost|127\.0\.0\.1/i)
  })
})
