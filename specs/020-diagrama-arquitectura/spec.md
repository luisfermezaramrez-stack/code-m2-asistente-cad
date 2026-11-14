# SPEC-020 — Diagrama de arquitectura actualizado y enlace al tablero

- **ID**: SPEC-020
- **Tipo**: refactor (documentación viva; sin cambio de comportamiento)
- **Historia**: #68 (HU-19)
- **Responsable**: Luis Fernando Meza
- **Rama**: `docs/arquitectura-archify`
- **Estado**: Implementada, PR pendiente
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Problema y contexto

El diagrama de Archify (`docs/arquitectura.json` → `docs/arquitectura.html`) se generó
antes de HU-14, HU-15 y HU-16. Muestra una arquitectura que ya no existe: interfaz
Gradio en `:7860`, traducción ES→EN con la API Gemini y un servidor llama.cpp con GPU.
Le faltan la SPA en Vue servida por FastAPI, el progreso por SSE, DeepSeek por API y
MLflow. El README lo marca como «Pendiente (HU-14)» y no enlaza el tablero Kanban, que
la rúbrica del M3 exige enlazar desde el README.

## Historia de usuario

**Como** evaluador o desarrollador nuevo, **quiero** un diagrama de arquitectura que
coincida con el sistema que corre hoy y un enlace al tablero desde el README, **para**
entender el runtime y la gestión del proyecto sin leer el código.

## Requisitos

### Funcionales

- **RF-1**: `docs/arquitectura.json` describe el runtime actual: diseñador CAD, SPA Vue,
  API FastAPI con SSE, gestor de trabajos, pipeline, verificación y B-rep, salidas,
  registro, seguimiento MLflow, servidor MLflow y API DeepSeek.
- **RF-2**: no quedan componentes retirados (Gradio, traducción, Gemini, llama.cpp).
- **RF-3**: cada componente interno cita su evidencia en el código (ruta y líneas) en una
  revisión fija del repositorio.
- **RF-4**: `docs/arquitectura.html` se regenera con `archify deliver`, nunca a mano.
- **RF-5**: el README enlaza el tablero
  `https://github.com/users/luisfermezaramrez-stack/projects/1/views/1` y retira el aviso
  «Pendiente (HU-14)».

### No funcionales

- **RNF-1**: `archify validate --quality showcase` sin errores ni advertencias.
- **RNF-2**: 8 a 12 componentes y un camino principal resaltado.

## Criterios de aceptación

### AC1 — Runtime actual

- **Dado** `docs/arquitectura.json`
- **Cuando** se listan sus componentes
- **Entonces** aparecen la SPA Vue, FastAPI con SSE, DeepSeek y MLflow, y no aparecen
  Gradio, Gemini, la traducción ni llama.cpp.

### AC2 — Evidencia verificable

- **Dado** el JSON con `meta.repository.revision` fijada
- **Cuando** se ejecuta `archify validate architecture docs/arquitectura.json --quality showcase --repo-root .`
- **Entonces** termina con `ok: true`, 0 errores y 0 advertencias.

### AC3 — HTML regenerado

- **Dado** el JSON validado
- **Cuando** se ejecuta `archify deliver`
- **Entonces** `docs/arquitectura.html` y `docs/arquitectura.delivery.json` se actualizan
  y el recibo de entrega queda en estado `current`.

### AC4 — README

- **Dado** el README
- **Cuando** se revisa la sección de arquitectura y la de gestión
- **Entonces** enlaza el tablero y ya no tiene el aviso «Pendiente (HU-14)».

## Fuera de alcance

- Otros tipos de diagrama (secuencia, flujo de datos).
- Cambios en el código de la aplicación.

## Métricas de éxito

- 0 componentes retirados en el diagrama y validación `showcase` sin hallazgos.
