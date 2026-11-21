# SPEC-058 · HU-57 — `main` como única rama de integración (refactor de proceso)

- **ID**: SPEC-058
- **Historia**: #119 (HU-57) · 1 SP · Etiquetas: chore, infra, documentation
- **Responsable**: Luis Meza
- **Rama**: `chore/hu-57-flujo-main`
- **Estado**: Spec-first · en revisión (PR #120)
- **Resuelve**: la decisión abierta de [SPEC-056](../056-hu-55-releases-automaticos/spec.md)
  ("rama de release"): los releases se cortan desde `main`.

## Problema y contexto

Las PR van a `develop` (`CONSTITUTION.md` §7; `CONTRIBUTING.md`), pero la rama por defecto
del repositorio es `main`. GitHub sólo cierra una issue con `Closes #N` cuando la PR se
fusiona en la rama por defecto, así que ninguna issue se cierra sola: hay que cerrarlas y
moverlas a Done a mano en el tablero.

Además, `develop` concentra todo lo que asegura la calidad:

- La CI corre sólo en PRs y pushes a `develop` (`.github/workflows/ci.yml:3-7`).
- Dependabot abre sus PR contra `develop` (`.github/dependabot.yml`, tres ecosistemas).
- `develop` exige el check `test`, una aprobación y conversaciones resueltas; `main` no
  tiene protección de rama.

`main` sólo recibe merges de entrega desde `develop`, sin contenido propio.

## Historia de usuario

**Como** integrante del equipo, **quiero** que todo el trabajo entre por PR directamente a
`main`, **para** que las issues se cierren solas al fusionar y el flujo tenga una sola rama
de integración.

## Requisitos

### Funcionales

- **RF-1**: antes de retirar `develop`, todo su contenido queda fusionado en `main` (PR
  `develop` → `main`).
- **RF-2**: la CI corre en PRs y pushes a `main`.
- **RF-3**: Dependabot abre sus PR contra `main`.
- **RF-4**: `main` tiene la misma protección que hoy tiene `develop`: check `test` en verde
  y actualizado, una aprobación, revisiones obsoletas descartadas, conversaciones resueltas,
  sin force-push ni borrado, aplicada también a administradores.
- **RF-5**: `CONSTITUTION.md`, `CONTRIBUTING.md`, `AGENTS.md`, el README, `data/README.md` y
  las plantillas de `.github/` describen `main` como única rama de integración; el badge de
  CI apunta a `main`.
- **RF-6**: las entregas son etiquetas sobre `main`; no hay rama de entregas separada.
- **RF-7**: las PR abiertas contra `develop` se redirigen a `main`.
- **RF-8**: la rama `develop` se elimina del remoto cuando RF-1 a RF-7 estén fusionados. La
  elimina el responsable a mano; ningún proceso automático la borra.

### No funcionales

- **RNF-1**: no se reescriben los documentos históricos (informe final, specs cerradas,
  evidencias de HU): describen el flujo vigente en su momento.
- **RNF-2**: no cambia el contenido de las etiquetas `v1.0` y `v1.0.1`.

## Criterios de aceptación

### AC1 — Cierre automático

- **Dado** una PR a `main` con `Closes #N` en la descripción
- **Cuando** se fusiona
- **Entonces** la issue `#N` queda cerrada sin intervención manual.

### AC2 — CI sobre `main`

- **Dado** una PR abierta contra `main`
- **Cuando** se crea o actualiza
- **Entonces** corre el workflow `CI` y su check `test` bloquea la fusión si falla.

### AC3 — Sin referencias vigentes a `develop`

- **Dado** el repositorio tras el cambio
- **Cuando** se buscan referencias a `develop` en `.github/`, `CONSTITUTION.md`,
  `CONTRIBUTING.md`, `AGENTS.md`, `README.md` y `data/README.md`
- **Entonces** sólo quedan menciones históricas (§9 de la constitución) y la tarea pendiente
  de eliminar `develop` (§10).

### AC4 — Nada se pierde

- **Dado** `develop` y `main` antes de borrar `develop`
- **Cuando** se ejecuta `git rev-list --count origin/main..origin/develop`
- **Entonces** el resultado es `0`, o los commits restantes son sólo merges sin contenido.

## Fuera de alcance

- Automatizar releases (SPEC-056).
- Cambiar la convención de nombres de rama o de commits.
- Reescribir el historial de Git.

## Métricas de éxito

- 100 % de las issues con `Closes #N` cerradas al fusionar su PR.
- Una sola rama de larga vida (`main`).
