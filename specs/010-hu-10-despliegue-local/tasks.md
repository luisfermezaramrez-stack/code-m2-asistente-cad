# SPEC-010 · HU-10 — Tareas del despliegue local

- **ID**: SPEC-010 · **Historia**: #10 · **Responsable**: Juan Camilo Pérez
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Cada tarea se marca `[x]` al cerrarse, con su evidencia.

## 1. Despliegue (AC1, AC2, AC5)

- [ ] T01 — Verificar que `docker-compose.yml` levanta `api` (con la SPA) y `mlflow` sin
      referencias a Gradio ni a `:7860`. · Hecho cuando: `make up` deja ambos
      contenedores saludables en una máquina limpia. · Depende de: —
- [ ] T02 — Comprobar `http://localhost:8000` (SPA), `/health` (200) y `/docs`. ·
      Hecho cuando: las tres URLs responden. · Depende de: T01
- [ ] T03 — Comprobar que `make down` no deja contenedores del proyecto (`docker ps`). ·
      Depende de: T01

## 2. Prueba de humo y latencia (AC3, AC4)

- [ ] T04 — Escribir `tests/test_smoke_deploy.py` en rojo: p50/p90, CSV de salida y
      código de salida 1 ante un fallo, con `httpx.MockTransport`. · Depende de: —
- [ ] T05 — Implementar `scripts/smoke_deploy.py` hasta poner T04 en verde. · Depende de: T04
- [ ] T06 — Correr la prueba de humo con 5 solicitudes (una por familia) contra el
      servicio desplegado. · Hecho cuando: 5/5 válidas. · Depende de: T01, T05
- [ ] T07 — Correr ≥ 30 solicitudes del banco y registrar p50/p90. · Hecho cuando:
      p90 ≤ 60 s o la brecha queda explicada. · Depende de: T06

## 3. Documentación y cierre (AC5)

- [ ] T08 — Actualizar el README: requisitos, `make up`, URLs (`:8000`, `:5000`),
      prueba de humo y `make down`. · Depende de: T07
- [ ] T09 — Guardar la evidencia en `specs/010-hu-10-despliegue-local/evidence.md`
      (salida de humo, p50/p90, captura de `docker ps`). · Depende de: T07
- [ ] T10 — `make check` en verde y PR hacia `develop` con `Closes #10` y enlace a esta
      spec. · Depende de: T08, T09
