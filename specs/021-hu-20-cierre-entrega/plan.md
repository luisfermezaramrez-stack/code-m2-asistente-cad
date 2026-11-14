# SPEC-021 — Plan del cierre de la entrega

- **ID**: SPEC-021 · **Historia**: HU-20 · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## 1. Diseño

Flujo de entrega:

```text
docs/hu-20-cierre-entrega → PR a develop (Closes #72) → CI verde
  → PR develop → main → git tag -a v1.0 → git push origin v1.0
```

Cambios por archivo:

| Archivo | Cambio | AC |
| --- | --- | --- |
| `docs/informe-final.md` | Objetivo 4 = 8/9 (simulado); resumen sin «sin medir»; tablero 20/20; enlace al proyecto 1; nota de `v1.0` | AC1, AC2, AC5 |
| `specs/017-hu-13-informe-final/spec.md` | Estado «Implementada»; HU-11 como prueba simulada | AC3 |
| `specs/017-hu-13-informe-final/tasks.md` | Marcar T02–T08 con evidencia; T01 queda como supuesto declarado | AC3 |
| `specs/README.md` | Estados reales del índice y fila de SPEC-021 | RF-7 |
| Issue #13 | Marcar AC1–AC5 | AC3 |

## 2. Decisiones

| Decisión | Porqué |
| --- | --- |
| Nueva historia en lugar de reabrir #13 | #13 ya está en Done; una historia nueva deja trazable qué se corrigió y por qué. |
| Reportar el objetivo 4 como «cumplido (simulado)» | SPEC-006 redefinió la HU-11 como prueba simulada; ocultar ese matiz sería engañoso. |
| `v1.0` después de la promoción a `main` | SPEC-017 RF-4 exige la etiqueta sobre el commit de `main` que contiene el informe. |

## 3. Comandos

```bash
make check
gh project item-list 1 --owner luisfermezaramrez-stack --format json \
  --jq '[.items[].status]|group_by(.)|map({(.[0]):length})|add'
git tag -a v1.0 -m "v1.0 — entrega final M2" <commit-main>
git push origin v1.0
git ls-remote --tags origin v1.0
```

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El conteo del tablero cambia al agregar HU-20 | Se reporta el conteo del día de la actualización e incluye HU-20 en el total. |
| Conflictos al promover `develop` a `main` | PR de promoción con CI; sin `--force`. |
| Enlaces relativos rotos | Verificación con un script que comprueba que cada ruta existe (AC5). |

## 5. Verificación

- Revisión del informe contra `docs/prueba-usuarios.md` y el tablero (AC1, AC2).
- Revisión de SPEC-017 y del issue #13 (AC3).
- `git ls-remote --tags origin v1.0` (AC4).
- Script de enlaces relativos (AC5).
