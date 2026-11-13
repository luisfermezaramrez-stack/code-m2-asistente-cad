import { describe, expect, it } from 'vitest'
import { parseJob } from '../src/api'
import { event } from './fakeCadService'

describe('contrato de respuesta (datos simulados)', () => {
  it.each([null, {}, { resultado: 'desconocido' }, { ...event('error', 1), estado: 'desconocido' }])('rechaza respuestas desconocidas sin tratarlas como éxito', (value) => {
    expect(() => parseJob(value)).toThrow('Respuesta inválida')
  })
})
