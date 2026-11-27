/**
 * SPEC-042 RF-2 / AC3: declinación con su motivo visible. El backend simulado
 * declina; la UI debe mostrarlo tal cual y no ofrecer archivos.
 */
import { expect, test } from '@playwright/test'
import { enviarSolicitud } from './support/acciones'
import { event, servirBackend } from './support/fakeCadService'

const MOTIVO = 'Fuera del catálogo admitido'

test.describe('declinación', () => {
  test('muestra el motivo de la declinación sin archivos', async ({ page }) => {
    await servirBackend(page, {
      frames: [event('validando', 1), event('declinado', 2, { motivo: MOTIVO })],
    })

    await enviarSolicitud(page)

    const estado = page.locator('.state')
    await expect(estado).toHaveClass(/declinado/)
    await expect(estado).toContainText('Solicitud declinada')
    await expect(estado).toContainText(MOTIVO)

    await expect(page.locator('.steps li')).toHaveText(['Validando solicitud', 'Solicitud declinada'])
    await expect(page.locator('button.download')).toHaveCount(0)
    await expect(page.getByText('No hay archivos disponibles.')).toBeVisible()
    // No se inventa geometría sustituta ni se ofrece descarga.
    await expect(page.getByText('No hay archivo STEP disponible.')).toHaveCount(0)
  })
})
