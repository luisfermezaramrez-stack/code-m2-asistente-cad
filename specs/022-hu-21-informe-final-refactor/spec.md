# SPEC-022 · HU-21 — Refactor del informe final y la trazabilidad de la HU-13

- **ID**: SPEC-022
- **Tipo**: refactor (documentación viva; sin cambio de comportamiento)
- **Historia**: #73 (HU-21) · 2 SP · Etiquetas: documentation, refactor · Hito: M3
- **Responsable**: Luis Fernando Meza
- **Rama**: `docs/hu-21-informe-final-refactor`
- **Estado**: Implementada, PR pendiente de revisión
- **Relacionada**: SPEC-017 (HU-13, #13), SPEC-006 (HU-11, #11), SPEC-021 (HU-20, #72,
  depende de esta)
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Problema y contexto

La HU-13 (#13) está cerrada y en Done, pero su validación del 2026-11-14 encontró que
el informe y su trazabilidad quedaron desactualizados:

| AC de HU-13 | Hallazgo |
| --- | --- |
| AC1 | `docs/informe-final.md` reporta el objetivo 4 como «No medido / Pendiente», pero `docs/prueba-usuarios.md` ya registra **8/9** tareas sin ayuda (simulado; meta ≥ 7/9). |
| AC2 | El enlace al tablero es genérico (`?tab=projects`), no apunta al proyecto. |
| AC3 | El informe dice **16/19** en Done con brechas #11, #13 y #68; esas historias ya están en Done. |

Además, SPEC-017 sigue «Especificada, pendiente de implementación», su `tasks.md` tiene
1 de 8 tareas marcadas, los AC del issue #13 están sin marcar, y SPEC-017 y el informe
aún hablan de «3 usuarios externos» para la HU-11, que se redefinió como prueba
simulada con los integrantes del grupo (SPEC-006).

La publicación (promoción a `main` y etiqueta `v1.0`, AC4 y AC5 de HU-13) queda fuera:
la cubre SPEC-021 (HU-20, #72).

## Historia de usuario

**Como** docente evaluador, **quiero** que el informe final y la trazabilidad de la HU-13
reflejen el estado real del proyecto, **para** verificar el cumplimiento sin encontrar
datos contradictorios entre el informe, el tablero y la evidencia.

## Requisitos

### Funcionales

- **RF-1**: `docs/informe-final.md` reporta el objetivo 4 con el valor **8/9** de
  `docs/prueba-usuarios.md`, estado «Cumplido (simulado)» y la aclaración de que la
  prueba se hizo con los integrantes del grupo.
- **RF-2**: la sección «Estado del tablero» reporta las historias en Done sobre el total
  del tablero el día de la actualización y explica como brecha solo las que no estén en
  Done (por ejemplo HU-20 y HU-21 mientras sigan abiertas). Los gaps técnicos
  documentados se mantienen.
- **RF-3**: el enlace al tablero apunta a
  `https://github.com/users/luisfermezaramrez-stack/projects/1/views/1`.
- **RF-4**: el resumen del informe y SPEC-017 dejan de mencionar «usuarios externos»
  para la HU-11.
- **RF-5**: SPEC-017 pasa a estado «Implementada», su `tasks.md` marca las tareas
  cumplidas con evidencia (T08 remite a SPEC-021), y el issue #13 marca sus AC cumplidos
  (AC4 y AC5 remiten a #72).
- **RF-6**: el índice `specs/README.md` refleja el estado real de SPEC-006, SPEC-010,
  SPEC-016, SPEC-017, SPEC-019, SPEC-020, SPEC-021 y esta spec.

### No funcionales

- **RNF-1**: cada valor del informe cita su fuente versionada; no se hacen mediciones
  nuevas.
- **RNF-2**: todos los enlaces relativos del informe resuelven a archivos existentes.
- **RNF-3**: `make check` en verde.

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

### AC4 — Índice de specs

- **Dado** `specs/README.md`
- **Cuando** se compara con los issues y PR de cada spec
- **Entonces** el estado de cada fila coincide con la realidad.

### AC5 — Enlaces y verificación

- **Dado** el informe actualizado
- **Cuando** se verifican sus enlaces relativos y se ejecuta `make check`
- **Entonces** todos los enlaces resuelven a archivos existentes y `make check` termina
  en verde.

## Fuera de alcance

- Promoción a `main` y etiqueta `v1.0` (SPEC-021, HU-20).
- Nuevas mediciones o una prueba con usuarios externos reales.
- Resolver los gaps técnicos ya documentados (HU-15 T18, HU-14 T12, HU-12 T08/T09/T11,
  HU-02 T13/T15, gate MLflow p95, revisión humana de los STEP).
- Confirmar T01 de SPEC-017 contra la propuesta del M2 (no versionada en el repo); se
  mantiene declarado como supuesto.

## Métricas de éxito

- 4/4 objetivos con valor medido y fuente; conteo del tablero igual al real; 0 enlaces
  rotos.
