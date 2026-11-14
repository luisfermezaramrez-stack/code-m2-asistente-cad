# SPEC-021 · HU-20 — Publicación de la entrega en `main` con la etiqueta `v1.0`

- **ID**: SPEC-021
- **Tipo**: Spec-first (entrega; sin cambio de comportamiento)
- **Historia**: #72 (HU-20) · 1 SP · Etiquetas: documentation, Testing · Hito: M3
- **Responsable**: Luis Fernando Meza
- **Rama**: `docs/hu-20-cierre-entrega` (spec); la promoción se hace con una PR
  `develop → main`
- **Estado**: Implementada (PR #75 y etiqueta `v1.0`, 2026-11-14)
- **Depende de**: SPEC-022 (HU-21, #73) — informe y trazabilidad de la HU-13 actualizados
- **Relacionada**: SPEC-017 (HU-13, #13)
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Problema y contexto

La HU-13 (#13) está cerrada y en Done, pero su validación del 2026-11-14 encontró que
sus criterios de publicación no se cumplieron:

| AC de HU-13 | Hallazgo |
| --- | --- |
| AC4 | No existe la etiqueta `v1.0`, ni local ni remota. |
| AC5 | El informe se fusionó en `develop` (PR #70), pero no está en `main`. |

SPEC-017 RF-4 exige la etiqueta anotada `v1.0` sobre el commit de `main` que contiene el
informe. La corrección del contenido del informe y de la trazabilidad de la HU-13 es
SPEC-022 (HU-21, #73); esta spec solo publica el resultado.

## Historia de usuario

**Como** docente evaluador, **quiero** que la entrega quede publicada en `main` con la
etiqueta `v1.0`, **para** verificar el cumplimiento sobre una versión fija y
reproducible del proyecto.

## Requisitos

### Funcionales

- **RF-1**: `develop` se promueve a `main` mediante una PR, después de fusionar la HU-21.
- **RF-2**: se crea y publica la etiqueta anotada `v1.0` sobre el commit de `main` que
  contiene el informe actualizado.
- **RF-3**: `docs/informe-final.md` y SPEC-017 T08 registran la etiqueta publicada.

### No funcionales

- **RNF-1**: `make check` y el CI en verde sobre el commit etiquetado.
- **RNF-2**: la promoción no usa `--force` ni reescribe historia de `main`.

## Criterios de aceptación

### AC1 — Promoción a `main`

- **Dado** la HU-21 fusionada en `develop` con CI en verde
- **Cuando** se fusiona la PR `develop → main`
- **Entonces** `main` contiene el informe actualizado de la HU-21.

### AC2 — Etiqueta publicada

- **Dado** el commit de `main` con el informe actualizado
- **Cuando** se ejecuta `git ls-remote --tags origin v1.0`
- **Entonces** existe la etiqueta anotada `v1.0` sobre ese commit.

### AC3 — Registro

- **Dado** la etiqueta publicada
- **Cuando** se revisan el informe y SPEC-017
- **Entonces** el informe menciona `v1.0` como publicada y SPEC-017 T08 está marcada con
  esa evidencia.

## Fuera de alcance

- Cambios de contenido del informe o de la trazabilidad de la HU-13 (SPEC-022, HU-21).
- GitHub Release con notas o binarios.

## Métricas de éxito

- `v1.0` publicada en el remoto sobre `main` con CI en verde.
