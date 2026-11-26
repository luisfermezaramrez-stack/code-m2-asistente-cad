# Tareas · HU-53 (SPEC-054)

Orden de ejecución; la evidencia final vive en [evidence.md](./evidence.md).

- [x] T0 · Leer SPEC-054, SPEC-037, `CONSTITUTION.md`, `api.py`, `trabajos.py`,
  `cola_trabajos.py`, `registro.py` y el frontend; auditoría no destructiva.
- [x] T1 · Redactar `plan.md` y `tasks.md` antes de escribir código.
- [x] T2 · Crear `src/m2_cad/autenticacion.py` y `src/m2_cad/usuarios.py`: hashes
  PBKDF2, sesiones HMAC, configuración por entorno y dependencia de usuario.
- [x] T3 · Añadir propietario a `Trabajo` y `GestorTrabajos` sin romper las firmas
  existentes; al integrar `main`, también en la cola de HU-45 y su worker.
- [x] T4 · Añadir columna `usuario` al registro con migración de CSV antiguos y
  trazabilidad en MLflow.
- [x] T5 · Integrar `/auth/login`, `/auth/logout`, `/auth/me` y exigir usuario en
  generación, consulta, cancelación, descargas y registros; `/health` y `/ready` abiertos.
- [x] T6 · Implementar inicio/cierre de sesión en el frontend y bloquear la generación
  sin sesión cuando la autenticación esté activa.
- [x] T7 · Escribir `tests/test_hu53_autenticacion.py` y pruebas frontend para AC1–AC4,
  expiración/firma de cookie y modo local.
- [x] T8 · Documentar `.env.example`, `README.md`, `Makefile`, `CONSTITUTION.md`,
  `specs/README.md` y el smoke HTTP en la misma rama.
- [x] T9 · Ejecutar Ruff, pytest con cobertura, `api-types`, Vitest/typecheck/build y
  pre-commit; abrir PR #133 y escribir `evidence.md`.
