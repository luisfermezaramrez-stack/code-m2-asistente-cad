# Evidencia · HU-39 (SPEC-040)

- **Rama**: `feature/hu-39-visor-ortogonal-medidas` (desde `origin/main` @ `094fe9b`).
- **Issue**: #99 · **PR**: [#148](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/148) (`Closes #99`).
- **Fecha**: 2026-11-27.
- **Entorno**: checkout local Windows; `npm ci` ejecutado con `make frontend-install`. Para `make check` se usaron variables temporales de sesión (`UV_NO_SYNC=1`, `PYTHONPATH=src`, `M2_DOWNLOAD_SECRET` de 32+ bytes) para no recompilar `python-solvespace` (requiere MSVC) y satisfacer el secreto de descargas.

## Criterios de aceptación

| AC | Verificación |
|----|--------------|
| AC1 · Vistas reproducibles | `frontend/tests/GlbViewer.test.ts` selecciona dos veces cada una de las tres vistas sobre un modelo simulado de caja 40×30×5; compara posición y zoom registrados en cada `render()` y comprueba `aria-pressed`. Pasan las 3 vistas. |
| AC2 · Vistas exportables | La misma suite descarga `vista-frontal-mm.png` desde un PNG simulado y verifica la cabecera `data:image/png;base64,`; con el lienzo vacío muestra `No se pudo capturar la vista` y no genera otra descarga. |
| AC3 · Medidas coherentes con `caja_mm` | `frontend/tests/viewerMedidas.test.ts` valida el parseo de `40.00x30.00x5.00`, el rechazo de formatos CSV, la tolerancia relativa del ±2 % (40.8 dentro, 40.9 fuera) y las tres cotas etiquetadas. `GlbViewer.test.ts` comprueba que el componente muestra `40.00 mm`, `30.00 mm` y `5.00 mm` desde la prop `cajaMm`, sin leer el CSV. |
| AC4 · Ajuste de unidades | Al seleccionar `in`, las cotas pasan a `1.57 in`, `1.18 in` y `0.20 in`; la captura posterior se nombra `vista-frontal-in.png`. Helper: `25.4 mm = 1 in`. |

## RNF

- RNF-1: permanecen los seis botones de control y los atajos de flechas, `+`, `−` e `Inicio`; se añaden `1`/`2`/`3` para vistas y `U` para unidades, documentados en `#viewer-help`.
- RNF-2: `vi.mock` de `three`, `GLTFLoader`, `OrbitControls` y `RoomEnvironment`, con `fetch` y `ResizeObserver` simulados; ninguna prueba usa GPU, red, API key ni modelo remoto.
- RNF-3: `OrthographicCamera` calcula el frustum desde la caja y la relación de aspecto; `aplicarVista` fija dirección canónica, objetivo en el origen y `zoom = 1`, de modo que repetir la vista da la misma cámara.
- RNF-4: `WebGLRenderer({ preserveDrawingBuffer: true })` más un `render()` inmediato antes de `toDataURL('image/png')`.

## Comandos ejecutados

```text
make frontend-install
  added 182 packages, audited 183 packages

make frontend-test
  Test Files 11 passed (11)
  Tests 92 passed (92)

make frontend-typecheck
  vue-tsc --noEmit → sin errores

make check  (con las variables temporales indicadas)
  Ruff: All checks passed!
  verify_prompts.py: 2 versión(es) verificadas
  generate_api_contract.py --check: Contrato OpenAPI v1 actualizado.
  generate_api_types.py --check: Tipos OpenAPI actualizados.
  frontend-test: 11 archivos / 92 pruebas OK
  frontend-typecheck: OK
  frontend-build: ✓ built in 454ms
  pytest: 690 passed, 6 failed, 92.00 % de cobertura (umbral 70 % superado)
```

## Fallos locales no atribuibles a HU-39

Los seis fallos restantes de `pytest` son del checkout Windows y reproducen limitaciones del entorno, no tocan código frontend ni los archivos de esta HU:

1. `tests/test_api_edicion.py::test_b3_un_indice_ajeno_corrupto_es_indistinguible_de_uno_inexistente` — `PermissionError [WinError 5]` al `os.replace` sobre `data/cola.json` (OneDrive bloquea el reemplazo atómico).
2. `tests/test_corpus_dorado.py::test_runner_sale_cero_sin_divergencias_y_uno_con_divergencia` — 7 huellas STEP distintas por la versión local de OpenCascade.
3. `tests/test_hu30_registro.py::test_ac1_80_solicitudes_simultaneas_sin_perdidas` — `msvcrt.locking` → `OSError [Errno 36] Resource deadlock avoided`.
4. `tests/test_hu30_retencion.py::test_ac4_no_sigue_enlaces_simbolicos` — `OSError [WinError 1314]`; el usuario no tiene privilegio para crear symlinks.
5. `tests/test_hu30_retencion.py::test_ac4_no_borra_directorio_con_enlace_interno` — misma causa `WinError 1314`.
6. `tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms` — `p95=175.0 ms` en esta máquina; objetivo ≤ 50 ms.

Nota: el aviso de chunk grande de `GlbViewer` en `vite build` ya existía en HU-38 y no cambia con esta HU.
