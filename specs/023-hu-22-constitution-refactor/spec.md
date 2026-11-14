# SPEC-023 · HU-22 — Refactor de CONSTITUTION.md al estado real de la entrega

- **ID**: SPEC-023
- **Tipo**: refactor (documentación viva; sin cambio de comportamiento)
- **Historia**: #77 (HU-22) · 1 SP · Etiquetas: documentation, refactor · Hito: M3
- **Responsable**: Luis Fernando Meza
- **Rama**: `docs/hu-22-constitution-refactor`
- **Estado**: Implementada, PR #78 en revisión
- **Relacionada**: SPEC-021 (HU-20, #72, publicación `v1.0`), SPEC-020 (HU-19, #68,
  diagrama), SPEC-022 (HU-21, #73)
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Problema y contexto

`CONSTITUTION.md` es la fuente única de verdad del proyecto, pero quedó congelada en el
estado del 2026-11-13. La revisión del 2026-11-14, tras publicar `v1.0`, encontró:

| Sección | Hallazgo |
| --- | --- |
| §0 Estado | «En construcción 🚧»; HU-16 «implementada en `feature/hu-16-mlflow`»; HU-05, 07, 10–13 y 15 «pendientes». Las 21 historias (#1–#13, #37, #39, #45, #59, #63, #68, #72, #73) están cerradas y `v1.0` está publicada en `main` (`0caa8ee`). |
| §4 Estructura | `specs/` descrito como «Spec Kit (001–009)»; existen 22 specs de tipo Spec Kit, Retroactiva y Spec-first. |
| §10 Pendientes | Lista HU-05, 07, 10–13 y 15 como pendientes y la regeneración del diagrama Archify, entregada en HU-19 (#68, PR #69). |
| `AGENTS.md` | Describe `specs/` como 001–017. |

Si el jurado abre la CONSTITUTION durante la sustentación, contradice el tablero, el
índice de specs y la demo.

## Historia de usuario

**Como** docente evaluador, **quiero** que `CONSTITUTION.md` refleje el estado real del
proyecto, **para** verificar la entrega sin encontrar contradicciones entre la fuente
única de verdad, el tablero y las specs.

## Requisitos

### Funcionales

- **RF-1**: §0 «Estado» declara la entrega `v1.0` publicada en `main` y las historias
  HU-01 a HU-21 cerradas, sin listar historias pendientes que ya están cerradas.
- **RF-2**: §4 describe `specs/` con su rango real (001–023) y sus tipos (Spec Kit,
  Retroactiva, Spec-first), remitiendo a `specs/README.md`.
- **RF-3**: §10 marca como cumplidas las historias pendientes ya cerradas y la
  regeneración del diagrama (HU-19).
- **RF-4**: §9 registra la decisión de este refactor con su motivo.
- **RF-5**: `AGENTS.md` describe `specs/` con el mismo rango que §4.
- **RF-6**: `specs/README.md` incluye la fila de SPEC-023.

### No funcionales

- **RNF-1**: cada afirmación de estado se apoya en una fuente verificable (issues, tablero,
  etiqueta `v1.0`, índice de specs); no se agregan mediciones nuevas.
- **RNF-2**: la etiqueta `v1.0` no se mueve ni se modifica; el cambio entra por `develop`.
- **RNF-3**: `make check` en verde.

## Criterios de aceptación

### AC1 — Estado real

- **Dado** el tablero con las historias HU-01 a HU-21 en Done y la etiqueta `v1.0` en `main`
- **Cuando** se lee §0 de `CONSTITUTION.md`
- **Entonces** el estado indica la entrega `v1.0` y no lista historias pendientes cerradas.

### AC2 — Estructura de specs

- **Dado** `specs/` con 23 carpetas numeradas
- **Cuando** se leen §4 de `CONSTITUTION.md` y `AGENTS.md`
- **Entonces** ambos describen el rango 001–023 y los tipos de spec.

### AC3 — Pendientes al día

- **Dado** §10 de `CONSTITUTION.md`
- **Cuando** se compara con los issues cerrados y la PR #69
- **Entonces** las historias y el diagrama entregados aparecen como cumplidos.

### AC4 — Trazabilidad

- **Dado** §9 de `CONSTITUTION.md` y `specs/README.md`
- **Cuando** se revisan
- **Entonces** §9 registra este refactor y el índice incluye SPEC-023.

### AC5 — Verificación

- **Dado** los archivos modificados
- **Cuando** se ejecuta `make check`
- **Entonces** termina en verde.

## Fuera de alcance

- Mover la etiqueta `v1.0` o publicar una `v1.0.1` en `main`.
- Actualizar `plan.md` de SPEC-009 (menciona Gradio y MLflow v2.x).
- Resolver los gaps técnicos documentados (revisión humana de los STEP de HU-07, gate
  MLflow p95, entre otros).
- Proteger las ramas `develop` y `main` en GitHub (pendiente de §10 que se conserva).

## Métricas de éxito

- 0 historias cerradas listadas como pendientes en `CONSTITUTION.md`; rango de specs
  igual en §4, `AGENTS.md` y `specs/README.md`.
