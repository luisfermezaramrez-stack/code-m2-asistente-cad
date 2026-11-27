# Tareas · HU-44 (SPEC-045)

Checklist completado en orden de ejecución; la evidencia está en [evidence.md](./evidence.md).

- [x] T0 · Leer spec, CONSTITUTION.md, AGENTS.md, `banco.py`, `llm_resiliente.py`,
  `prompts.py`, `corpus_dorado.py`, `Makefile` y `ci.yml`; crear la rama desde `origin/main`.
- [x] T1 · Redactar `plan.md` y `tasks.md` antes de escribir código.
- [x] T2 · Exponer `llm_resiliente.clave_cuerpo()` y `pipeline.cuerpo_planificador()`
  reutilizando la normalización y el cuerpo de la llamada real.
- [x] T3 · Crear `src/m2_cad/banco_replay.py`: esquema v1, validación de prompt/modelo,
  clave canónica, proveedor grabado, siembra desde el banco y grabación contra el proveedor real.
- [x] T4 · Generar `data/banco_replay.json` con las 40 respuestas de referencia y su metadata
  de prompt (`origen: referencia-banco`); el artefacto declara `planner-v1` y su hash.
- [x] T5 · Integrar `--replay`, `--respuestas` y `--umbral` en `banco.main` sin alterar
  `make bench`; resumen con cero tokens, salida 1 bajo umbral y salida 2 si el artefacto falla.
- [x] T6 · Añadir `scripts/verify_banco_replay.py`, `make bench-replay`, el paso en
  `ci.yml` y el workflow programado `banco-baseline.yml` con MLflow y artefactos.
- [x] T7 · Crear `tests/test_hu44_banco_replay.py` con 7 pruebas para AC1–AC3, ausencia de
  red, cero tokens, grabación faltante, cambio de prompt, umbral y script de verificación.
- [x] T8 · Documentar en `README.md` y actualizar `CONSTITUTION.md` y `specs/README.md`
  en la misma rama.
- [x] T9 · Ejecutar Ruff, pytest (7 nuevas + 96 relacionadas + suite completa con cobertura
  91.67 %), contratos, prompts y frontend; registrar resultados y limitaciones en `evidence.md`.
  PR [#151](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/151) abierto y registrado en la evidencia y en el índice de specs.
