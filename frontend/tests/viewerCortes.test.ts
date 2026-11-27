import { describe, expect, it } from 'vitest'
import {
  constanteCorte,
  estadoInicialCorte,
  etiquetaCorte,
  fijarPosicion,
  limitesCorte,
  normalCorte,
  posicionMedia,
} from '../src/viewerCortes'
import type { EjeCorte, EstadoCorte } from '../src/viewerCortes'

const caja = { ancho: 40, fondo: 30, alto: 5 }
const activo = (eje: EjeCorte, posicion: number, invertido = false): EstadoCorte => ({
  activo: true,
  eje,
  posicion,
  invertido,
})

describe('viewerCortes · HU-50', () => {
  it('empieza desactivado en el eje Z', () => {
    const estado = estadoInicialCorte()

    expect(estado).toEqual({ activo: false, eje: 'z', posicion: 0, invertido: false })
  })

  it('calcula la posición media y los límites de cada eje', () => {
    expect(posicionMedia(caja, 'z')).toBe(2.5)
    expect(posicionMedia(caja, 'x')).toBe(20)
    expect(limitesCorte(caja, 'y')).toEqual({ min: 0, max: 30 })
  })

  it('acota la posición al rango de la caja', () => {
    expect(fijarPosicion(caja, 'z', -3)).toBe(0)
    expect(fijarPosicion(caja, 'z', 9)).toBe(5)
    expect(fijarPosicion(caja, 'z', Number.NaN)).toBe(0)
  })

  it('deriva la normal canónica y su inversión', () => {
    expect(normalCorte('z', false)).toEqual([0, 0, 1])
    expect(normalCorte('x', true)).toEqual([-1, 0, 0])
    expect(normalCorte('y', false)).toEqual([0, 1, 0])
  })

  it('coloca el plano a media altura y respeta la inversión', () => {
    expect(constanteCorte(caja, activo('z', 2.5))).toBe(0)
    expect(constanteCorte(caja, activo('z', 4))).toBe(-1.5)
    expect(constanteCorte(caja, activo('z', 4, true))).toBe(1.5)
  })

  it('anuncia el corte en la unidad elegida', () => {
    expect(etiquetaCorte(estadoInicialCorte(), caja, 'mm')).toContain('desactivado')

    const texto = etiquetaCorte(activo('z', 2.5, true), caja, 'mm')

    expect(texto).toContain('Z (alto)')
    expect(texto).toContain('2.50 mm')
    expect(texto).toContain('lado invertido')
    expect(etiquetaCorte(activo('x', 25.4), caja, 'in')).toContain('1.00 in')
  })
})
