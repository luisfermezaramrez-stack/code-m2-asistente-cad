# SPEC-017 · HU-13 — Informe final de métricas y entrega

- **ID**: SPEC-017
- **Historia**: #13 · 1 SP · Etiquetas: Testing · CPM: Q (día 15)
- **Responsable**: compartida (Juan Camilo Pérez, Carlos Eduardo Trujillo, Luis Fernando Meza)
- **Rama**: `feature/hu-13-informe-final`
- **Estado**: Implementada (PR #70); contenido actualizado por SPEC-022 (HU-21, #73);
  publicación en `main` con `v1.0` en SPEC-021 (HU-20, #72)
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Problema y contexto

El docente debe verificar el cumplimiento del proyecto sin recorrer el repositorio caso
por caso. Las metas ya están declaradas en el README (sección «Metas (objetivos 1–4)»),
pero los valores medidos están dispersos: banco en SPEC-016 (HU-07), latencia en
SPEC-010 (HU-10), autonomía de usuarios en SPEC-006 (HU-11) y DeepSeek en SPEC-008
(HU-14). Falta un documento único con meta, valor medido, estado y enlaces.

## Historia de usuario

**Como** docente evaluador, **quiero** un informe final con la meta y el valor medido de
cada objetivo, más los enlaces al repositorio, al tablero y al reporte del banco,
**para** verificar el cumplimiento del proyecto el día 15.

## Requisitos

### Funcionales

- **RF-1**: `docs/informe-final.md` con una tabla por objetivo: meta, valor medido,
  estado (cumplido / no cumplido) y fuente de la evidencia.
- **RF-2**: enlaces al repositorio, al tablero de GitHub Projects y al reporte del banco
  (`docs/reporte-banco.md`, SPEC-016).
- **RF-3**: estado del tablero: historias en Done sobre el total y brecha explicada por
  cada historia que no esté en Done.
- **RF-4**: etiqueta anotada `v1.0` sobre el commit de `main` que contiene el informe.

### No funcionales

- **RNF-1**: cada valor medido cita su fuente versionada (archivo, corrida o PR); no hay
  valores sin evidencia.
- **RNF-2**: el informe se enlaza desde el README.

## Objetivos evaluados

Tomados de la tabla «Metas (objetivos 1–4)» del README. *Supuesto a confirmar con la
propuesta del M2:* la correspondencia objetivo ↔ indicador es la siguiente.

| Objetivo | Indicador | Meta | Fuente prevista |
| --- | --- | --- | --- |
| 1 | Construcción conforme (±2 % volumen / caja) | ≥ 26/30 | SPEC-016 |
| 2 | Declinación correcta | ≥ 8/10 | SPEC-016 |
| 3 | Latencia p90 (solicitud → STEP) | ≤ 60 s | SPEC-010 |
| 4 | Autonomía de usuarios (tareas sin ayuda) | ≥ 7/9 | SPEC-006 (prueba simulada con los integrantes del grupo) |
| — | Reproducibilidad | 1 comando, CI en verde | CI de `develop` |

## Criterios de aceptación

### AC1 — Metas y valores

- **Dado** las evidencias de SPEC-006, SPEC-010 y SPEC-016
- **Cuando** se abre `docs/informe-final.md`
- **Entonces** cada uno de los 4 objetivos muestra meta, valor medido, estado y enlace a
  su evidencia.

### AC2 — Enlaces

- **Dado** el informe
- **Cuando** se siguen sus enlaces
- **Entonces** llevan al repositorio, al tablero y al reporte del banco, y ninguno está roto.

### AC3 — Estado del tablero

- **Dado** el tablero el día de la entrega
- **Cuando** se compara con el informe
- **Entonces** el informe reporta las historias en Done sobre el total del tablero (el
  plan original tenía 13; hoy hay 16, de HU-01 a HU-16) y explica la brecha de cada una
  que no esté en Done.

### AC4 — Etiqueta

- **Dado** el informe fusionado en `main`
- **Cuando** se ejecuta `git tag -l v1.0`
- **Entonces** existe la etiqueta anotada `v1.0` sobre ese commit.

### AC5 — Plazo

- **Dado** el cronograma del proyecto
- **Cuando** se entrega el informe
- **Entonces** su PR se fusiona antes del cierre del día 15.

## Fuera de alcance

- Nuevas mediciones: el informe solo consolida las de SPEC-006, SPEC-010 y SPEC-016.
- Diapositivas o video.

## Métricas de éxito

- 4/4 objetivos con valor medido y fuente; 0 enlaces rotos; `v1.0` publicada.
