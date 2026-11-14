# SPEC-022 — Plan del refactor del informe final

- **ID**: SPEC-022 · **Tipo**: refactor · **Historia**: HU-21 · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## 1. Diseño

Cambios por archivo:

| Archivo | Cambio | AC |
| --- | --- | --- |
| `docs/informe-final.md` | Objetivo 4 = 8/9 (simulado); resumen sin «sin medir»; tablero Done/total real; enlace al proyecto 1 | AC1, AC2, AC5 |
| `specs/017-hu-13-informe-final/spec.md` | Estado «Implementada»; HU-11 como prueba simulada | AC3 |
| `specs/017-hu-13-informe-final/tasks.md` | Marcar T02–T07 con evidencia; T01 como supuesto declarado; T08 remite a SPEC-021 | AC3 |
| `specs/README.md` | Estados reales del índice | AC4 |
| Issue #13 | Marcar AC1–AC3; AC4–AC5 remiten a #72 | AC3 |

## 2. Decisiones

| Decisión | Porqué |
| --- | --- |
| Historia nueva de tipo refactor en lugar de reabrir #13 | #13 ya está en Done; una historia nueva deja trazable qué se corrigió y por qué, igual que HU-18 y HU-19. |
| Separar contenido (HU-21) de publicación (HU-20) | La publicación en `main` y `v1.0` es una decisión de entrega distinta y depende de que el contenido esté correcto. |
| Reportar el objetivo 4 como «cumplido (simulado)» | SPEC-006 redefinió la HU-11 como prueba simulada; ocultar ese matiz sería engañoso. |

## 3. Comandos

```bash
gh project item-list 1 --owner luisfermezaramrez-stack --format json \
  --jq '[.items[].status]|group_by(.)|map({(.[0]):length})|add'
make check
```

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El conteo del tablero cambia mientras HU-20 y HU-21 están abiertas | Se reporta el conteo del día y se listan como brecha con su causa. |
| Enlaces relativos rotos | Verificación con un script que comprueba que cada ruta existe (AC5). |

## 5. Verificación

- Revisión del informe contra `docs/prueba-usuarios.md` y el tablero (AC1, AC2).
- Revisión de SPEC-017 y del issue #13 (AC3).
- Revisión del índice contra issues y PR (AC4).
- Script de enlaces relativos y `make check` (AC5).
