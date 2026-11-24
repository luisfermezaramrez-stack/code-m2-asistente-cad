# Plan · HU-27 — Tipos desde OpenAPI

## Base y alcance

- Rama: `feature/hu-27-tipos-openapi`, desde `origin/main` (`a824e56`).
- Fuente: `app.openapi()`, el mismo esquema servido en `/openapi.json`.
- Declarar `EstadoTrabajo` como `TypedDict` con campos opcionales `NotRequired`:
  mantiene la ausencia de campos y evita insertar `null` o valores por defecto.
- GET y DELETE de generaciones comparten el modelo; DELETE documenta 200 y 202.
  SSE conserva su esquema de transporte de texto y documenta el JSON de `data`
  mediante `x-event-data-schema`, referenciando el mismo modelo.
- La respuesta JSON de `/generar` continúa siendo un diccionario de cadenas.
- `Job` y `Stage` serán alias de los tipos generados. `Format` y `Artifact`
  describen controles/enlaces locales de la UI, no respuestas JSON del backend.
  `parseJob` continúa validando los datos en ejecución.

## Generación y controles

1. Usar `@hey-api/openapi-ts` fijado en el lockfile npm, con sólo el plugin
   TypeScript (sin generar SDK HTTP). Admite el TypeScript 6 del proyecto;
   `openapi-typescript` 7.13 exige TypeScript 5 y no se fuerza ese peer dependency.
2. Un script Python obtiene el esquema en memoria y lo pasa por stdin al generador
   Node. El generador trabaja en un directorio temporal, sin servidor, claves,
   inferencia, kernel CAD ni descargas durante la generación.
3. `make api-types` actualiza `frontend/src/generated/api.ts`, normalizado a UTF-8/LF.
4. `make api-types-check` compara en memoria, sin modificar el archivo, y ante
   divergencias indica `make api-types`. Forma parte de `make check` y de CI.
5. Probar el rechazo de un cambio de campo sin regeneración, la determinación
   del resultado y la preservación de estados/eventos, incluidos campos ausentes.

## Verificación

- `make api-types` y `make api-types-check` (AC2).
- Prueba de mutación del esquema: comparación falla y muestra el comando (AC1).
- `make check`: Ruff, sincronización de tipos, Vitest, vue-tsc, build y pytest
  con cobertura mínima del 70 % (AC3).
- Registrar los resultados reales y cualquier bloqueo de entorno en `tasks.md`.
