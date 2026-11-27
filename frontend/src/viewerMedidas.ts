export type Vista = 'frontal' | 'superior' | 'lateral'
export type VistaActiva = Vista | 'libre'
export type Unidad = 'mm' | 'in'
export type Eje = 'ancho' | 'fondo' | 'alto'

export const VISTAS: readonly Vista[] = ['frontal', 'superior', 'lateral']
export const ETIQUETAS_VISTA: Record<Vista, string> = {
  frontal: 'Frontal', superior: 'Superior', lateral: 'Lateral',
}
export const ETIQUETAS_EJE: Record<Eje, string> = {
  ancho: 'Ancho (X)', fondo: 'Fondo (Y)', alto: 'Alto (Z)',
}
export const DIRECCION_VISTA: Record<Vista, readonly [number, number, number]> = {
  frontal: [0, 0, 1], superior: [0, 1, 0], lateral: [1, 0, 0],
}
export const MM_POR_PULGADA = 25.4
export const TOLERANCIA_RELATIVA = 0.02

export interface CajaMm { ancho: number; fondo: number; alto: number }
export interface Medida { eje: Eje; texto: string }

export function parseCajaMm(valor: unknown): CajaMm | null {
  if (typeof valor !== 'string') return null
  const partes = valor.trim().toLowerCase().split('x')
  if (partes.length !== 3) return null
  const numeros = partes.map((parte) => Number(parte.trim()))
  if (numeros.some((numero) => !Number.isFinite(numero) || numero <= 0)) return null
  const [ancho = 0, fondo = 0, alto = 0] = numeros
  return { ancho, fondo, alto }
}

export function convertirMedida(valor: number, unidad: Unidad): number {
  return unidad === 'mm' ? valor : valor / MM_POR_PULGADA
}

export function formatearMedida(valor: number, unidad: Unidad): string {
  return `${convertirMedida(valor, unidad).toFixed(2)} ${unidad}`
}

export function medidasCaja(caja: CajaMm, unidad: Unidad): Medida[] {
  return [
    { eje: 'ancho', texto: formatearMedida(caja.ancho, unidad) },
    { eje: 'fondo', texto: formatearMedida(caja.fondo, unidad) },
    { eje: 'alto', texto: formatearMedida(caja.alto, unidad) },
  ]
}

export function dentroDeTolerancia(valor: number, referencia: number, tolerancia = TOLERANCIA_RELATIVA): boolean {
  if (referencia <= 0 || !Number.isFinite(valor) || !Number.isFinite(referencia)) return false
  return Math.abs(valor - referencia) / referencia <= tolerancia
}

export function posicionVista(vista: Vista, radio: number): readonly [number, number, number] {
  const [x = 0, y = 0, z = 0] = DIRECCION_VISTA[vista]
  const distancia = radio * 3
  return [x * distancia, y * distancia, z * distancia]
}

export function nombreArchivo(vista: VistaActiva, unidad: Unidad): string {
  return `vista-${vista}-${unidad}.png`
}
