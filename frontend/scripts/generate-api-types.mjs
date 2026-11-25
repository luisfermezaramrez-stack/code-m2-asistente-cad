// SPEC-028: sólo tipos, sin SDK, servidor ni acceso a red.
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createClient } from '@hey-api/openapi-ts'

let input = ''
process.stdin.setEncoding('utf8')
for await (const chunk of process.stdin) input += chunk
const directory = await mkdtemp(join(tmpdir(), 'm2-openapi-'))
try {
  await createClient({
    input: JSON.parse(input),
    output: { path: directory, format: false, lint: false },
    plugins: ['@hey-api/typescript'],
    logs: { level: 'silent' },
  })
  const types = await readFile(join(directory, 'types.gen.ts'), 'utf8')
  process.stdout.write('// Generado con make api-types. No editar a mano.\n' + types)
} finally {
  await rm(directory, { recursive: true, force: true })
}
