import { formatearMedida, type CajaMm, type Unidad } from './viewerMedidas'

export type EjeCorte = 'x' | 'y' | 'z'

export interface EstadoCorte {
  activo: boolean
  eje: EjeCorte
  posicion: number
  invertido: boolean
}

export const EJES_CORTE: readonly EjeCorte[] = ['x', 'y', 'z']
export const ETIQUETAS_CORTE: Record<EjeCorte, string> = {
  x: 'X (ancho)',
  y: 'Y (fondo)',
  z: 'Z (alto)',
}
export const TECLAS_CORTE: Record<string, EjeCorte> = { '4': 'x', '5': 'y', '6': 'z' }

export function estadoInicialCorte(): EstadoCorte {
  return { activo: false, eje: 'z', posicion: 0, invertido: false }
}

export function dimensionCorte(caja: CajaMm | null, eje: EjeCorte): number {
  if (!caja) return 0
  if (eje === 'x') return caja.ancho
  if (eje === 'y') return caja.fondo
  return caja.alto
}

export function posicionMedia(caja: CajaMm | null, eje: EjeCorte): number {
  return dimensionCorte(caja, eje) / 2
}

export function limitesCorte(caja: CajaMm | null, eje: EjeCorte): { min: number; max: number } {
  return { min: 0, max: dimensionCorte(caja, eje) }
}

export function fijarPosicion(caja: CajaMm | null, eje: EjeCorte, posicion: number): number {
  const { min, max } = limitesCorte(caja, eje)
  if (!Number.isFinite(posicion) || max <= 0) return min
  return Math.min(max, Math.max(min, posicion))
}

export function normalCorte(eje: EjeCorte, invertido: boolean): readonly [number, number, number] {
  const signo = invertido ? -1 : 1
  if (eje === 'x') return [signo, 0, 0]
  if (eje === 'y') return [0, signo, 0]
  return [0, 0, signo]
}

export function constanteCorte(caja: CajaMm | null, estado: EstadoCorte): number {
  const desplazamiento = fijarPosicion(caja, estado.eje, estado.posicion) - posicionMedia(caja, estado.eje)
  if (desplazamiento === 0) return 0
  return (estado.invertido ? 1 : -1) * desplazamiento
}

export function etiquetaCorte(estado: EstadoCorte, caja: CajaMm | null, unidad: Unidad): string {
  if (!estado.activo) return 'Corte desactivado; se muestra la pieza completa.'
  const posicion = formatearMedida(fijarPosicion(caja, estado.eje, estado.posicion), unidad)
  const inversion = estado.invertido ? ', lado invertido' : ''
  return `Corte ${ETIQUETAS_CORTE[estado.eje]} activo a ${posicion}${inversion}.`
}
