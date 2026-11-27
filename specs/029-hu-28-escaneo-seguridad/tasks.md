# SPEC-029 — HU-28 · Tareas

## Fase 1 — Especificación

- [x] Revisar SPEC-029, el workflow de GitHub, el pipeline espejo y la paridad ya vigilada.
- [x] Fijar herramientas: gitleaks `8.30.1` (sha256 del asset), pip-audit `2.10.1`, uv `0.13.5`.
- [x] Decidir que el escaneo es un objetivo propio (`make security`) fuera de `make check`.
- [x] Redactar `plan.md` y `tasks.md`.

## Fase 2 — Implementación

- [x] T1 — `seguridad_ci.py`: clasificación de la auditoría y mensajes en español (AC2).
- [x] T2 — Escaneo de secretos con gitleaks fijado y mensaje con archivo, línea y pasos (AC1).
- [x] T3 — Política de excepciones y validador con fecha de revisión (AC3).
- [x] T4 — Jobs en GitHub Actions y en el espejo de GitLab, con paridad vigilada.

## Fase 3 — Calidad

- [x] AC1: caso que falla con secreto falso y caso que pasa, con salida registrada.
- [x] AC2: caso que falla con CVE alto y caso que pasa, con salida registrada.
- [x] AC3: excepción justificada y vigente que desbloquea; vencida que falla.
- [x] Estado de `main` verificado y hallazgos reales documentados, sin silenciar.
- [x] `make check` en verde y `CONSTITUTION.md` actualizada.
