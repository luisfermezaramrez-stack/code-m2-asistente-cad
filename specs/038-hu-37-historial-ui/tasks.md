# Tareas · HU-37 (SPEC-038)

Checklist en orden de ejecución; la evidencia observada está en [evidence.md](./evidence.md).

- [x] T0 · Leer SPEC-038 completa, `CONSTITUTION.md` y `AGENTS.md`; crear `feature/hu-37-historial-ui` desde `origin/main` (`3363859`) en un worktree aparte, sin tocar la checkout principal.
- [x] T1 · Reconocer `/v1` (HU-31) y el historial de versiones (HU-35) para no duplicar endpoints, y documentar el mapa real del registro y de los tokens de descarga en `odd/tasks/hu-37-historial-ui.md`.
- [x] T2 · Backend: `GET /v1/registros` con `RespuestaRegistros`/`RegistroResumen`, filtros `resultado` y `texto`, sólo filas propias, orden descendente y tope de 200 (AC3, RF-2, S6). Prueba ROJO observada antes de implementar.
- [x] T3 · Backend: lector público `registro.listar`/`registro.leer` y reutilización por `api._leer_registro` sin cambiar su contrato (404/422).
- [x] T4 · Backend: `X-Download-Token` en `GET /v1/registros/{identificador}` tras sesión y propiedad, que habilita el STEP de una solicitud antigua tras el reinicio (RF-4, AC4). Prueba ROJO observada.
- [x] T5 · Contrato y tipos regenerados con `make api-contract` y `make api-types`; ambos `--check` en verde (S9).
- [x] T6 · UI: `HistoryView` con el listado real, filtros servidos por el backend, estados derivados de la carga y sin lectura de `?estado=` (RF-1, RF-2, S2). Pruebas Vitest ROJO observadas.
- [x] T7 · UI: reapertura en `/historial/:identificador` con estado, motivo, descarga del STEP y visor GLB sólo si el trabajo vive (RF-3, RF-4). Pruebas Vitest ROJO observadas.
- [x] T8 · Corrección de coherencia: `GET /v1/registros/{identificador}` expone `estado` y `motivo` derivados y el cliente deja de reimplementar la precedencia (RNF-1). ROJO observado en pytest y Vitest.
- [x] T9 · Documentación: `plan.md`, `tasks.md`, `evidence.md`, `CONSTITUTION.md`, `README.md` e índice de `specs/README.md`.
- [x] T10 · `make check`, commits por unidad de trabajo, push y PR [#145](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/145) hacia `main` con `Closes #97` (sin mergear).
