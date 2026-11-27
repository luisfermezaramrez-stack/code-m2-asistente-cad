export type EstadoVista = 'vacio' | 'cargando' | 'error'

export function estadoDesdeConsulta(valor: unknown): EstadoVista {
  return valor === 'cargando' || valor === 'error' ? valor : 'vacio'
}
