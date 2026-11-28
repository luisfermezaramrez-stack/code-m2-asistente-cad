import { expect, type Page } from '@playwright/test'

/** Descripción de ejemplo; el modelo no se invoca: el backend está simulado. */
export const DESCRIPCION = 'Placa de 120 × 120 mm, espesor de 6 mm y 4 agujeros de 12 mm en un círculo de 90 mm.'

/**
 * Navega a la vista de solicitud del shell y envía la descripción. Sin esperas
 * fijas: se espera por la vista y por la respuesta del backend simulado.
 */
export async function enviarSolicitud(page: Page, texto: string = DESCRIPCION): Promise<void> {
  await page.goto('/')
  await expect(page).toHaveURL(/\/nueva-solicitud$/)
  await expect(page.getByRole('heading', { name: 'Especifica la pieza que necesitas' })).toBeVisible()
  await page.locator('#descripcion').fill(texto)
  await page.getByRole('button', { name: 'Generar pieza' }).click()
}
