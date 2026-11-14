# SPEC-023 — Plan del refactor de CONSTITUTION.md

- **ID**: SPEC-023 · **Tipo**: refactor · **Historia**: HU-22 · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## 1. Diseño

Cambios por archivo:

| Archivo | Cambio | AC |
| --- | --- | --- |
| `CONSTITUTION.md` §0 | Estado «Entregada ✅ — `v1.0` en `main`»; HU-01 a HU-21 cerradas | AC1 |
| `CONSTITUTION.md` §4 | `specs/` con rango 001–023 y tipos | AC2 |
| `CONSTITUTION.md` §9 | Fila de la decisión de este refactor | AC4 |
| `CONSTITUTION.md` §10 | Marcar historias y diagrama entregados | AC3 |
| `AGENTS.md` | `specs/` con rango 001–023 | AC2 |
| `specs/README.md` | Fila SPEC-023 | AC4 |

## 2. Decisiones

| Decisión | Porqué |
| --- | --- |
| Historia nueva de tipo refactor en lugar de reabrir #72 | #72 ya está en Done y `v1.0` publicada; una historia nueva deja trazable qué se corrigió y por qué, igual que HU-18, HU-19 y HU-21. |
| No mover `v1.0` | Una etiqueta publicada es inmutable; moverla reescribe la entrega evaluable. Si la corrección debe llegar a `main`, se publica como `v1.0.1` en otra historia. |
| Conservar en §9 las decisiones históricas (Gradio, Gemini) | §9 es un historial: las filas antiguas documentan decisiones que luego se reemplazaron, y ya tienen su fila de reemplazo. |

## 3. Comandos

```bash
gh project item-list 1 --owner luisfermezaramrez-stack --format json \
  --jq '[.items[].status]|group_by(.)|map({(.[0]):length})|add'
git log -1 --format='%h %ci' v1.0
make check
```

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El estado vuelve a desactualizarse con historias nuevas | La directiva de mantenimiento de la CONSTITUTION exige actualizarla en el mismo commit de cada cambio significativo. |
| Confundir el refactor con un cambio de la entrega | RNF-2: el cambio entra solo por `develop`; `v1.0` no se toca. |

## 5. Verificación

- Revisión de §0 y §10 contra los issues cerrados, el tablero y la etiqueta `v1.0` (AC1, AC3).
- Revisión de §4, `AGENTS.md` y `specs/README.md` contra `ls specs/` (AC2, AC4).
- `make check` (AC5).
