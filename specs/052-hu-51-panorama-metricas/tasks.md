# SPEC-052 — HU-51 · Tareas

## Fase 1 — Especificación

- [x] Revisar SPEC-052, la API actual y lo que MLflow ya registra por corrida.
- [x] Decidir fuente única (MLflow), ventana y estado degradado.
- [x] Redactar `plan.md` y `tasks.md`.

## Fase 2 — Implementación

- [x] T1 — `src/m2_cad/metricas.py` y `tests/test_metricas.py`.
- [x] T2 — `GET /v1/metricas` y contrato regenerado.
- [x] T3 — `MetricsView.vue`, ruta, navegación y prueba de la vista.
- [x] T4 — `make check` en verde y contrato/tipos regenerados.

## Fase 3 — Calidad

- [x] AC1: totales, causas, latencia media y costo.
- [x] AC2: estado degradado sin 500, visible en la UI.
- [x] AC3: costo acumulado y enlace a MLflow en la vista.
