/**
 * SPEC-042 RF-1 / AC3: flujo feliz en un navegador real — solicitud, progreso
 * informado por el servidor y pieza entregada con descarga autorizada.
 */
import { expect, test } from '@playwright/test'
import { enviarSolicitud } from './support/acciones'
import { event, servirBackend, TOKEN_DESCARGA } from './support/fakeCadService'

test.describe('flujo feliz', () => {
  test('informa el progreso y entrega la pieza verificada', async ({ page }) => {
    const backend = await servirBackend(page, {
      frames: [
        event('validando', 1),
        event('generando', 2),
        event('verificado', 3, { resultado: { step: 'pieza.step', glb: 'pieza.glb', bom_csv: 'bom.csv' } }),
      ],
    })

    await enviarSolicitud(page)

    const estado = page.locator('.state')
    await expect(estado).toHaveClass(/verificado/)
    await expect(estado).toContainText('Pieza verificada')
    await expect(estado).toContainText('Verificación geométrica completada.')

    // El progreso que se muestra es el que informó el servidor, en orden.
    await expect(page.locator('.steps li')).toHaveText([
      'Validando solicitud',
      'Generando pieza',
      'Pieza verificada',
    ])

    const descargas = page.locator('button.download')
    await expect(descargas).toHaveCount(3)
    await expect(page.locator('[data-download-filename="pieza.step"]')).toBeVisible()

    // La descarga del STEP viaja con el token de la respuesta SSE.
    const descargaPrometida = page.waitForEvent('download')
    await page.locator('[data-download-filename="pieza.step"]').click()
    const descarga = await descargaPrometida
    expect(descarga.suggestedFilename()).toBe('pieza.step')
    // El visor 3D pidió el GLB y la descarga pidió el STEP, ambos con token.
    expect(backend.descargas.sort()).toEqual(['glb', 'step'])
    expect(backend.peticiones.filter((peticion) => peticion.path.includes('/archivos/'))
      .every((peticion) => peticion.token === TOKEN_DESCARGA)).toBe(true)

    // La entrega se anuncia como preliminar en el resultado, no con un aviso fijo del shell.
    await expect(page.locator('.notice')).toHaveCount(0)
  })
})
