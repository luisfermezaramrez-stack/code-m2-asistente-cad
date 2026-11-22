# Tareas · HU-27

- [x] T01: revisar SPEC-028, confirmar `main` y crear rama de trabajo.
- [x] T02: fijar alcance y estrategia en `plan.md`.
- [x] T03: modelar el estado compartido GET/DELETE/SSE sin cambiar sus cuerpos.
- [x] T04: añadir generador offline determinista y tipos versionables.
- [x] T05: consumir tipos generados en el cliente conservando `parseJob`.
- [x] T06: integrar generación/comprobación en Makefile y CI.
- [x] T07: cubrir divergencia de contrato y preservación HTTP/SSE.
- [x] T08: actualizar documentación y CONSTITUTION.
- [x] T09: ejecutar controles y registrar evidencia.
- [ ] T10: confirmar CI verde y revisión antes de aceptar/cerrar #87.

## Evidencia

Verificación local del 2026-11-22:

- Ruff: correcto.
- Hooks pre-commit sobre los archivos de HU-27: correctos (Ruff, formato,
  tamaño, espacios, fin de archivo, YAML y JSON).
- `make api-types` / `make api-types-check`: generación y comparación correctas
  (con las variables de entorno indicadas abajo).
- Vitest: 50 pruebas correctas; `vue-tsc --noEmit` y build Vite correctos.
- Pytest: 318 correctas y 1 fallo; cobertura 96,56 % (umbral: 70 %).
  Las 8 pruebas de `tests/test_api_types.py` pasaron, incluida la mutación real
  del esquema: renombrar `estado` sin regenerar devuelve fallo con el comando
  `make api-types`; la comprobación no modifica el archivo.
- Único fallo: `tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms`,
  p95 192,5 ms frente a 50 ms. Es una medición de MLflow; ni ese módulo ni esa
  prueba se modifican en HU-27. No se presenta `make check` como verde.

### Entorno y límites

`make check` sin ajustes intenta compilar `python-solvespace` y falla por falta
de Microsoft C++ Build Tools. El entorno local previo tampoco tenía MLflow;
se preparó un entorno temporal con `uv`, conservando las dependencias fijadas
en `uv.lock`, salvo los dos paquetes nativos siguientes:

```powershell
$env:UV_PROJECT_ENVIRONMENT='C:\Users\cetd9\AppData\Local\Temp\opencode\hu27-venv'
$env:UV_LINK_MODE='copy'
uv sync --locked --dev --no-install-package python-solvespace --no-install-package llama-cpp-python
$env:UV_NO_SYNC='1'
make check
```

La suite se ejecutó completa, sin exclusiones de pruebas, con los resultados
anteriores. Esto no demuestra la instalación nativa completa en Windows.
CI conserva su instalación completa en Ubuntu. No hubo llamadas al proveedor
LLM ni se requiere Docker para la generación. La aceptación final sigue pendiente.
