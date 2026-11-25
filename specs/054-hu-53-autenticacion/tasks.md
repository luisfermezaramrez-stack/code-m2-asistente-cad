# Tareas · HU-53 (SPEC-054)

Orden de ejecución; la evidencia final vive en [evidence.md](./evidence.md).

- [ ] T0 · Leer SPEC-054, SPEC-037, `CONSTITUTION.md`, `api.py`, `trabajos.py`,
  `cola_trabajos.py`, `registro.py` y el frontend; auditoría no destructiva.
- [ ] T1 · Redactar `plan.md` y `tasks.md` antes de escribir código.
- [ ] T2 · Crear `src/m2_cad/autenticacion.py` y `src/m2_cad/usuarios.py`: hashes
  PBKDF2, sesiones HMAC, configuración por entorno y dependencia de usuario.
- [ ] T3 · Añadir propietario a `Trabajo` y `GestorTrabajos` sin romper las firmas
  existentes (la rama parte de `main`, sin la cola de HU-45).
- [ ] T4 · Añadir columna `usuario` al registro con migración de CSV antiguos y
  trazabilidad en MLflow.
- [ ] T5 · Integrar `/auth/login`, `/auth/logout`, `/auth/me` y exigir usuario en
  generación, consulta, cancelación, descargas y registros; `/health` y `/ready` abiertos.
- [ ] T6 · Implementar inicio/cierre de sesión en el frontend y bloquear la generación
  sin sesión cuando la autenticación esté activa.
- [ ] T7 · Escribir `tests/test_hu53_autenticacion.py` y pruebas frontend para AC1–AC4,
  expiración/firma de cookie y modo local.
- [ ] T8 · Documentar `.env.example`, `README.md`, `Makefile`, `CONSTITUTION.md`,
  `specs/README.md` y el smoke HTTP en la misma rama.
- [x] T9 · Ejecutar Ruff, pytest con cobertura, `api-types`, Vitest/typecheck/build y
  pre-commit; abrir PR #133 y escribir `evidence.md`.
