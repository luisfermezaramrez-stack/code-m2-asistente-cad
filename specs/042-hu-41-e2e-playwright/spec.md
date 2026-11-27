# SPEC-042 · HU-41 — E2E del frontend con Playwright en CI

- **ID**: SPEC-042
- **Historia**: #101 (HU-41) · 2 SP · Etiquetas: Testing, Frontend · Hito: M4
- **Planificación**: Ola 2 · Tamaño M · Épica: Calidad
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: [SPEC-039](../039-hu-38-app-shell/spec.md)
- **Rama**: `feature/hu-41-e2e-playwright`
- **Estado**: En revisión (PR [#144](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/144)); `plan.md`, `tasks.md` y `evidence.md` completos
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5

## Problema y contexto

El frontend tiene 32 casos Vitest en `frontend/tests/` (26 en `App.test.ts`, 5 en
`sse.test.ts` y 1 en `api.test.ts`), que prueban componentes y el cliente SSE con un
servicio simulado (`frontend/tests/fakeCadService.ts`). No hay Playwright ni directorio
`e2e/`: ninguna prueba ejercita el flujo en un navegador real, de la descripción a la
descarga.

Una regresión de integración (rutas del shell de SPEC-039, eventos SSE, descargas) puede
pasar Vitest y romper el flujo para el usuario.

## Historia de usuario

**Como** equipo de desarrollo, **quiero** pruebas E2E del flujo principal en CI, **para**
que una regresión de UI que rompa el flujo feliz se detecte antes de fusionar.

## Requisitos

### Funcionales

- **RF-1**: escenario E2E del flujo feliz: solicitud, progreso y pieza entregada.
- **RF-2**: escenario E2E de declinación con su motivo visible.
- **RF-3**: escenario E2E de error del modelo.
- **RF-4**: los escenarios corren contra un backend simulado.
- **RF-5**: la suite corre en CI y, ante un fallo, publica captura y traza como
  artefactos.

### No funcionales

- **RNF-1**: sin red externa, API key ni GPU: el modelo y el backend se simulan.
- **RNF-2**: los escenarios son deterministas (sin esperas fijas dependientes de tiempo).
- **RNF-3**: no reemplaza la suite Vitest existente.

## Criterios de aceptación

### AC1 — Regresión detectada

- **Dado** un cambio de UI que rompe el flujo feliz
- **Cuando** corre CI
- **Entonces** el job E2E falla.

### AC2 — Evidencia en el fallo

- **Dado** un escenario E2E fallido en CI
- **Cuando** termina el job
- **Entonces** quedan disponibles como artefactos la captura y la traza de Playwright.

### AC3 — Cobertura de los tres flujos

- **Dado** la suite E2E
- **Cuando** se ejecuta sobre la rama principal
- **Entonces** pasan los escenarios feliz, de declinación y de error del modelo.

## Fuera de alcance

- Pruebas contra el modelo real o el núcleo geométrico real.
- Matriz de navegadores completa (Supuesto: basta un navegador en CI).
- Auditoría de accesibilidad (SPEC-041).

## Métricas de éxito

- Tres escenarios E2E verdes en CI.
- Toda falla E2E acompañada de captura y traza.
