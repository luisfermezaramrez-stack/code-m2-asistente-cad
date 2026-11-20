# SPEC-039 · HU-38 — App shell y navegación por vistas

- **ID**: SPEC-039
- **Historia**: #98 (HU-38) · 3 SP · Etiquetas: Frontend · Hito: M4
- **Planificación**: Ola 2 · Tamaño M · Épica: UX
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: [SPEC-035](../035-hu-34-sistema-diseno-v2/spec.md)
- **Rama**: `feature/hu-38-app-shell`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

Esta spec reformula el borrador 25 ("layout responsive"): la cosmética responsive ya
existe y no se reescribe.

1. `frontend/src/style.css:51` y `frontend/src/style.css:55` definen los breakpoints de
   900 px y 480 px.
2. `frontend/src/App.vue:36` incluye el skip link y `frontend/src/App.vue:70` la región
   `aria-live="polite"` del estado.
3. Toda la interfaz vive en una sola vista, `frontend/src/App.vue` (105 líneas), sin
   rutas: no hay URL que identifique una vista ni un resultado.

4. El servidor sólo sirve `/` y `/assets` (`src/m2_cad/web.py:42`, `:59-73`), sin
   fallback SPA, y `tests/test_web.py:44-52` afirma un 404 JSON para toda ruta
   desconocida, incluida `/ruta-desconocida`.
5. Los estados vacío, cargando, error y declinado ya se distinguen en la vista actual
   (`frontend/src/App.vue:16-23`, `frontend/src/App.vue:70-74`).

Lo que falta es estructura: un shell con navegación entre vistas y URLs compartibles,
sobre los tokens y la tipografía de SPEC-035. Introducir rutas exige un fallback SPA en
el servidor y cambiar esa prueba; ambos quedan dentro del alcance.

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
  Los de la vista actual ya existen; lo nuevo son los estados propios del shell (ruta
  desconocida y vistas de historial y ajustes).
- **RF-4**: el estado de cada vista es recuperable al abrir su URL directamente.
- **RF-5**: `src/m2_cad/web.py` añade un fallback SPA que entrega `index.html` en las
  rutas de las vistas, y `tests/test_web.py:44-52` se ajusta a ese contrato.

### No funcionales

- **RNF-1**: se conservan los breakpoints, el skip link y la región `aria-live`
  existentes.
- **RNF-2**: la navegación es operable sólo con teclado.
- **RNF-3**: las pruebas no usan red, API key ni GPU: el backend se simula.
- **RNF-4**: el servidor entrega la aplicación en las rutas nuevas sin romper el 404 JSON
  de las rutas API y de `/assets` desconocidas (`src/m2_cad/web.py:36-73`, registrado en
  `src/m2_cad/api.py:560`).

## Criterios de aceptación

### AC1 — URL propia por vista

- **Dado** el shell desplegado
- **Cuando** se navega a nueva solicitud, historial o ajustes
- **Entonces** cada vista muestra una URL distinta en la barra de direcciones.

### AC2 — Estado recuperable

- **Dado** la URL de una vista copiada en otra pestaña
- **Cuando** se abre
- **Entonces** se presenta la misma vista con su estado recuperado.

### AC3 — Estados nuevos del shell diferenciados

Los estados vacío, cargando, error y declinado de la vista actual ya se distinguen
(`App.vue:16-23`, `App.vue:70-74`) y se conservan como no regresión; este AC cubre sólo
los estados nuevos del shell.

- **Dado** una ruta de vista desconocida, o las vistas de historial y ajustes en estado
  vacío, cargando o error
- **Cuando** se muestra
- **Entonces** cada estado es visual y textualmente distinguible de los demás.

### AC4 — Navegación sólo con teclado

- **Dado** el shell sin uso del mouse
- **Cuando** se recorre con Tab, Shift+Tab y Enter
- **Entonces** se alcanzan y activan todas las entradas de navegación con foco visible.

### AC5 — Fallback SPA sin romper el 404 JSON

- **Dado** el servidor con el build de la interfaz
- **Cuando** se pide directamente la ruta de una vista y, por separado, una ruta API o un
  recurso de `/assets` inexistentes
- **Entonces** la vista recibe `index.html` y las otras dos conservan su 404 JSON (hoy la
  ruta de la vista responde 404 JSON).

## Fuera de alcance

- Contenido de la vista de historial (SPEC-038) y auditoría axe completa (SPEC-041).
- Nuevos tokens o modo oscuro (SPEC-035).
- Ajustes que requieran persistencia en el servidor (Supuesto: la vista de ajustes
  reúne las opciones que hoy existen en la UI).

## Métricas de éxito

- Tres vistas con URL propia y estado recuperable.
- Cero regresiones en las pruebas Vitest existentes.
