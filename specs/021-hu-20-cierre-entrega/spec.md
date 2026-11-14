# SPEC-021 · HU-20 — Cierre de la entrega: informe final actualizado y `v1.0`

- **ID**: SPEC-021
- **Tipo**: Spec-first (documentación y entrega; sin cambio de comportamiento)
- **Historia**: #72 (HU-20) · 2 SP · Etiquetas: documentation, Testing · Hito: M3
- **Responsable**: Luis Fernando Meza
- **Rama**: `docs/hu-20-cierre-entrega`
- **Estado**: Especificada, pendiente de implementación
- **Relacionada**: SPEC-017 (HU-13, #13), SPEC-006 (HU-11, #11), SPEC-020 (HU-19, #68)
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Problema y contexto

La HU-13 (#13) está cerrada y en Done, pero su validación del 2026-11-14 encontró que
no cumple del todo y que el informe quedó desactualizado:

| AC de HU-13 | Hallazgo |
| --- | --- |
| AC1 | `docs/informe-final.md` reporta el objetivo 4 como «No medido / Pendiente», pero `docs/prueba-usuarios.md` ya registra **8/9** tareas sin ayuda (simulado; meta ≥ 7/9). |
| AC2 | El enlace al tablero es genérico (`?tab=projects`), no apunta al proyecto. |
| AC3 | El informe dice **16/19** en Done con brechas #11, #13 y #68; el tablero tiene hoy **20/20** en Done. |
| AC4 | No existe la etiqueta `v1.0`, ni local ni remota. |
| AC5 | El informe está en `develop` (PR #70), pero no en `main`. |

Además, la trazabilidad SDD está atrasada: SPEC-017 sigue «Especificada, pendiente de
implementación», su `tasks.md` tiene 1 de 8 tareas marcadas, los AC del issue #13 están
sin marcar, y SPEC-017 y el informe aún hablan de «3 usuarios externos» para la HU-11,
que se redefinió como prueba simulada con los integrantes del grupo (SPEC-006).

## Historia de usuario

**Como** docente evaluador, **quiero** que el informe final refleje el estado real del
proyecto y que la entrega quede publicada en `main` con la etiqueta `v1.0`, **para**
verificar el cumplimiento sin encontrar datos contradictorios entre el informe, el
tablero y la evidencia.

## Requisitos

### Funcionales

- **RF-1**: `docs/informe-final.md` reporta el objetivo 4 con el valor **8/9** de
  `docs/prueba-usuarios.md`, estado «Cumplido (simulado)» y la aclaración de que la
  prueba se hizo con los integrantes del grupo.
- **RF-2**: la sección «Estado del tablero» reporta las historias en Done sobre el total
  del tablero el día de la actualización (hoy 20/20) y retira las brechas ya cerradas
  (#11, #13, #68). Los gaps técnicos documentados se mantienen.
- **RF-3**: el enlace al tablero apunta a
  `https://github.com/users/luisfermezaramrez-stack/projects/1/views/1`.
- **RF-4**: el resumen del informe y SPEC-017 dejan de mencionar «usuarios externos»
  para la HU-11.
- **RF-5**: SPEC-017 pasa a estado «Implementada», su `tasks.md` marca las tareas
  cumplidas con evidencia, y el issue #13 marca sus AC cumplidos.
- **RF-6**: `develop` se promueve a `main` y se publica la etiqueta anotada `v1.0` sobre
  el commit de `main` que contiene el informe actualizado.
- **RF-7**: el índice `specs/README.md` refleja el estado real de SPEC-006, SPEC-010,
  SPEC-016, SPEC-017, SPEC-019, SPEC-020 y esta spec.

### No funcionales

- **RNF-1**: cada valor del informe cita su fuente versionada; no se hacen mediciones
  nuevas.
- **RNF-2**: todos los enlaces relativos del informe resuelven a archivos existentes.
- **RNF-3**: `make check` en verde antes de la promoción a `main`.

## Criterios de aceptación

### AC1 — Objetivo 4 medido

- **Dado** `docs/prueba-usuarios.md` con 8/9 tareas sin ayuda
- **Cuando** se abre `docs/informe-final.md`
- **Entonces** el objetivo 4 muestra meta ≥ 7/9, valor 8/9, estado cumplido (simulado) y
  enlace a su evidencia, y el resumen ya no dice «sin medir».

### AC2 — Tablero coherente

- **Dado** el tablero el día de la actualización
- **Cuando** se compara con la sección «Estado del tablero»
- **Entonces** el conteo Done/total coincide, no se listan como brecha historias ya en
  Done y el enlace abre el proyecto 1.

### AC3 — Trazabilidad de HU-13

- **Dado** SPEC-017 y el issue #13
- **Cuando** se revisan
- **Entonces** SPEC-017 está en «Implementada», su `tasks.md` tiene las tareas cumplidas
  marcadas con evidencia y el issue #13 tiene sus AC marcados.

### AC4 — Publicación

- **Dado** el informe actualizado fusionado en `develop`
- **Cuando** se promueve a `main` y se ejecuta `git ls-remote --tags origin v1.0`
- **Entonces** existe la etiqueta anotada `v1.0` sobre el commit de `main` que contiene
  el informe.

### AC5 — Enlaces

- **Dado** el informe actualizado
- **Cuando** se verifican sus enlaces relativos
- **Entonces** todos resuelven a archivos existentes en el repositorio.

## Fuera de alcance

- Nuevas mediciones o una prueba con usuarios externos reales.
- Resolver los gaps técnicos ya documentados (HU-15 T18, HU-14 T12, HU-12 T08/T09/T11,
  HU-02 T13/T15, gate MLflow p95, revisión humana de los STEP).
- Confirmar T01 de SPEC-017 contra la propuesta del M2 (no versionada en el repo); se
  mantiene declarado como supuesto.

## Métricas de éxito

- 4/4 objetivos con valor medido y fuente; conteo del tablero igual al real; 0 enlaces
  rotos; `v1.0` publicada en el remoto.
