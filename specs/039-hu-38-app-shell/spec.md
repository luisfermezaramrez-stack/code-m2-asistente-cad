# SPEC-039 · HU-38 — App shell y navegación por vistas

- **ID**: SPEC-039
- **Historia**: issue por crear · Ola 2 · Tamaño M · Épica: UX
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: [SPEC-035](../035-hu-34-sistema-diseno-v2/spec.md)
- **Rama**: `feature/hu-38-app-shell`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5

## Problema y contexto

Esta spec reformula el borrador 25 ("layout responsive"): la cosmética responsive ya
existe y no se reescribe.

1. `frontend/src/style.css:51` y `frontend/src/style.css:55` definen los breakpoints de
   900 px y 480 px.
2. `frontend/src/App.vue:36` incluye el skip link y `frontend/src/App.vue:70` la región
   `aria-live="polite"` del estado.
3. Toda la interfaz vive en una sola vista, `frontend/src/App.vue` (105 líneas), sin
   rutas: no hay URL que identifique una vista ni un resultado.

Lo que falta es estructura: un shell con navegación entre vistas y URLs compartibles,
sobre los tokens y la tipografía de SPEC-035.

## Historia de usuario

**Como** usuario del asistente, **quiero** moverme entre nueva solicitud, historial y
ajustes con URLs propias, **para** compartir o recuperar una vista concreta y entender en
qué estado está mi solicitud.

## Requisitos

### Funcionales

- **RF-1**: un shell común con navegación entre "nueva solicitud", "historial" y
  "ajustes".
- **RF-2**: cada vista tiene una ruta con URL compartible.
- **RF-3**: los estados vacío, cargando, error y declinación se presentan diferenciados.
- **RF-4**: el estado de cada vista es recuperable al abrir su URL directamente.

### No funcionales

- **RNF-1**: se conservan los breakpoints, el skip link y la región `aria-live`
  existentes.
- **RNF-2**: la navegación es operable sólo con teclado.
- **RNF-3**: las pruebas no usan red, API key ni GPU: el backend se simula.
- **RNF-4**: el servidor entrega la aplicación en las rutas nuevas sin romper el 404 JSON
  de las rutas API desconocidas (`src/m2_cad/api.py:559`).

## Criterios de aceptación

### AC1 — URL propia por vista

- **Dado** el shell desplegado
- **Cuando** se navega a nueva solicitud, historial o ajustes
- **Entonces** cada vista muestra una URL distinta en la barra de direcciones.

### AC2 — Estado recuperable

- **Dado** la URL de una vista copiada en otra pestaña
- **Cuando** se abre
- **Entonces** se presenta la misma vista con su estado recuperado.

### AC3 — Estados diferenciados

- **Dado** una vista en estado vacío, cargando, error o declinación
- **Cuando** se muestra
- **Entonces** cada estado es visual y textualmente distinguible de los demás.

### AC4 — Navegación sólo con teclado

- **Dado** el shell sin uso del mouse
- **Cuando** se recorre con Tab, Shift+Tab y Enter
- **Entonces** se alcanzan y activan todas las entradas de navegación con foco visible.

## Fuera de alcance

- Contenido de la vista de historial (SPEC-038) y auditoría axe completa (SPEC-041).
- Nuevos tokens o modo oscuro (SPEC-035).
- Ajustes que requieran persistencia en el servidor (Supuesto: la vista de ajustes
  reúne las opciones que hoy existen en la UI).

## Métricas de éxito

- Tres vistas con URL propia y estado recuperable.
- Cero regresiones en las pruebas Vitest existentes.
