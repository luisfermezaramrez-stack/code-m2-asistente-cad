import { describe, expect, it } from 'vitest'
import {
  MM_POR_PULGADA, TOLERANCIA_RELATIVA, VISTAS, convertirMedida, dentroDeTolerancia, formatearMedida,
  medidasCaja, nombreArchivo, parseCajaMm, posicionVista,
} from '../src/viewerMedidas'

describe('viewerMedidas', () => {
  it('lee las cotas del formato texto de caja_mm', () => {
    const caja = parseCajaMm(' 40.00X30.00x5.00 ')

    expect(caja).toEqual({ ancho: 40, fondo: 30, alto: 5 })
  })

  it('no inventa cotas cuando el valor no es una caja_mm válida', () => {
    expect(parseCajaMm('40,30,5;0,00')).toBeNull()
    expect(parseCajaMm('40x30')).toBeNull()
    expect(parseCajaMm('40x0x5')).toBeNull()
    expect(parseCajaMm(undefined)).toBeNull()
  })

  it('convierte y formatea entre milímetros y pulgadas', () => {
    expect(convertirMedida(MM_POR_PULGADA, 'in')).toBe(1)
    expect(formatearMedida(30, 'mm')).toBe('30.00 mm')
    expect(formatearMedida(30, 'in')).toBe('1.18 in')
  })

  it('devuelve tres cotas etiquetadas y comparables contra la caja', () => {
    const caja = { ancho: 40, fondo: 30, alto: 5 }

    const medidas = medidasCaja(caja, 'mm')

    expect(medidas).toEqual([
      { eje: 'ancho', texto: '40.00 mm' },
      { eje: 'fondo', texto: '30.00 mm' },
      { eje: 'alto', texto: '5.00 mm' },
    ])
    expect(dentroDeTolerancia(40.8, caja.ancho)).toBe(true)
    expect(dentroDeTolerancia(40.9, caja.ancho)).toBe(false)
    expect(TOLERANCIA_RELATIVA).toBe(0.02)
  })

  it('define direcciones deterministas para las tres vistas ortogonales', () => {
    expect(VISTAS).toEqual(['frontal', 'superior', 'lateral'])
    expect(posicionVista('frontal', 10)).toEqual([0, 0, 30])
    expect(posicionVista('superior', 10)).toEqual([0, 30, 0])
    expect(posicionVista('lateral', 10)).toEqual([30, 0, 0])
    expect(posicionVista('lateral', 10)).toEqual(posicionVista('lateral', 10))
  })

  it('nombra las capturas según la vista y las unidades activas', () => {
    expect(nombreArchivo('superior', 'in')).toBe('vista-superior-in.png')
    expect(nombreArchivo('libre', 'mm')).toBe('vista-libre-mm.png')
  })
})
