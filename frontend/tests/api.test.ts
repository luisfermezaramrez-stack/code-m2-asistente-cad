import { describe, expect, it } from 'vitest'
import { parseJob, publicMessage } from '../src/api'
import { event } from './fakeCadService'

describe('contrato de respuesta (datos simulados)', () => {
  it.each([null, {}, { resultado: 'desconocido' }, { ...event('error', 1), estado: 'desconocido' }])('rechaza respuestas desconocidas sin tratarlas como éxito', (value) => {
    expect(() => parseJob(value)).toThrow('Respuesta inválida')
  })
})

describe('mensajes públicos de configuración', () => {
  const safe = 'El modelo no está configurado: falta DEEPSEEK_API_KEY.'

  it('permite únicamente el diagnóstico exacto sin valor de la clave', () => {
    expect(publicMessage(safe, 'Error genérico')).toBe(safe)
  })

  it.each([
    `${safe} DEEPSEEK_API_KEY=sk-secreto`,
    `${safe} Traceback: error interno`,
    `${safe} http://10.0.0.5:8080`,
    'DEEPSEEK_API_KEY=sk-secreto',
    'DeepSeek rechazó la API key: sk-secreto',
    'Bearer sk-secreto',
    'Traceback: error interno',
  ])('mantiene el filtro para secretos y errores internos: %s', (text) => {
    expect(publicMessage(text, 'Error genérico')).toBe('Error genérico')
  })
})
