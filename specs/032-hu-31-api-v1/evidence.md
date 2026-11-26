# HU-31 — Evidencia de cierre (SPEC-032)

- **Fecha:** 2026-11-26
- **Rama original:** `feature/hu-31-api-v1`
- **Rama de corrección:** `fix/hu-31-revisiones-pr130`
- **Base:** `origin/main` en `a71c3cc` (PR #130 ya fusionado)
- **PR:** [#130](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/130) (fusionado, con comentarios de revisión pendientes)
- **PR de corrección:** [#138](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/138)

## 1. Criterios de aceptación

| AC | Verificación | Resultado |
| --- | --- | --- |
| AC1 | `tests/test_hu31_api_v1.py`: mismos JSON, consulta y descarga STEP llamando a `/generar` y a `/v1/generar`; 9 rutas planas responden `307` con `Deprecation`, `Sunset` y `Link`; la query se conserva; la redirección respeta `root_path`; el proxy de Vite sirve `/v1` | ✅ |
| AC2 | `test_ac2_quitar_un_campo_del_esquema_rompe_el_contrato`: eliminar `EstadoTrabajo.estado` de una copia del esquema hace fallar `validar_contrato` con la ruta del campo | ✅ |
| AC3 | `test_ac3_el_openapi_publicado_solo_contiene_v1_y_esta_congelado`: `info.version == "1.0.0"`, todas las claves de `paths` empiezan con `/v1/` y coinciden con `contracts/openapi-v1.json` | ✅ |
| AC4 | `test_ac4_la_politica_de_deprecacion_esta_documentada`: `docs/versionado-api.md` contiene `90 días`, RFC 9745/8594, `Deprecation: @1795564800`, `Sunset: Tue, 23 Feb 2027 00:00:00 GMT`, `follow_redirects` y `curl -L` | ✅ |

## 2. Comandos y resultados

Ejecutados en macOS x86_64 con el entorno `.venv` existente. Se usa
`uv run --no-sync` en local porque `uv run --locked` intenta reconstruir
`nlopt==2.11.0` en esta arquitectura; CI mantiene `--locked` desde los lockfiles.
Para el suite completo se apartó temporalmente `data/registro.csv` generado por la
rama HU-53 (columna `usuario`), incompatible con el esquema de 8 columnas de `main`;
se restauró al terminar.

```text
$ uv run --no-sync ruff check src tests scripts/verify_hu15_deployment.py \
    scripts/generate_api_types.py scripts/generate_api_contract.py
All checks passed!

$ uv run --no-sync ruff format --check src tests scripts/generate_api_contract.py
45 files already formatted

$ uv run --no-sync python scripts/generate_api_contract.py --check
Contrato OpenAPI v1 actualizado.

$ uv run --no-sync python scripts/generate_api_types.py --check
Tipos OpenAPI actualizados.

$ M2_DOWNLOAD_SECRET=<secreto-efimero-de-64-bytes> \
    uv run --no-sync pytest -q --cov=m2_cad --cov-report=term-missing
435 passed, 1 deselected, 26 warnings in 51.95s
TOTAL 1842 stmts, 113 miss, 94% cover
Required test coverage of 70.0% reached. Total coverage: 93.87%

$ npm --prefix frontend test
Test Files  4 passed (4)
Tests       51 passed (51)

$ npm --prefix frontend run typecheck
(no errors)

$ npm --prefix frontend run build
✓ built in 929ms
```

`make check` queda cubierto por el equivalente local de sus seis pasos: Ruff,
`api-contract-check`, `api-types-check`, Vitest, TypeScript/build y pytest con cobertura.

CI del PR #130: run `45693889918` ✅ en 1 m 3 s, con todos los pasos verdes,
incluido el arranque integrado HTTP con modelo simulado y CAD real.

## 3. Aislamiento

- Sin red, API key ni GPU: el procesador se inyecta por `Callable`, MLflow se
  desactiva por dependencia y `LLM_BASE_URL` apunta a un host simulado.
- `M2_DOWNLOAD_SECRET` se define sólo en el entorno del comando de pruebas;
  nunca se versiona ni se usa un valor real.
- `data/*.lock` se ignora para no versionar el bloqueo del registro generado
  por las pruebas.

## 4. Cambios entregados

- `src/m2_cad/api.py`: `APIRouter(prefix="/v1")`, versión `1.0.0`, redirecciones
  planas `307` fuera del esquema y registro de entradas inválidas en `/v1/generar`.
- `src/m2_cad/contrato_api.py`, `contracts/openapi-v1.json`: contrato congelado
  determinista y comparación con diagnóstico de la primera divergencia.
- `scripts/generate_api_contract.py`, targets `api-contract` y
  `api-contract-check` (incluidos en `make check`).
- `docs/versionado-api.md`, `README.md`, `CONSTITUTION.md`, `.env.example`: política
  de 90 días configurable, formato RFC 9745/8594 y condición de seguimiento de
  redirecciones.
- SPA, scripts y evaluador HTTP consumen `/v1`; tipos TypeScript regenerados
  con el generador de SPEC-028 (sin edición manual).
- `frontend/vite.config.ts`: proxy reducido a `/v1`, con prueba de regresión en
  `frontend/tests/viteProxy.test.ts`.
- `Dockerfile`: `HEALTHCHECK` consulta `/v1/health`.
- `tests/test_hu31_api_v1.py` más ajustes de pruebas existentes que inspeccionan
  paths del OpenAPI o simulan el transporte HTTP.

## 5. Limitaciones

- No se publica `/v2` ni autenticación; ambas decisiones quedan fuera de alcance.
- Las redirecciones planas son temporales y se retirarán tras el `Sunset`.
- La compatibilidad de AC1 requiere que el cliente siga el `307` (`curl -L`,
  `follow_redirects=True`); un cliente que no lo haga debe reenviar a `Location`.
- El nombre del tipo generado cambia por el prefijo `/v1`; `frontend/src/api.ts`
  conserva el alias público `Job` para no propagar el renombrado al componente.
- El build del frontend avisa de un chunk > 500 kB (`GlbViewer`), advertencia
  preexistente no introducida por esta HU.
- `tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms`
  es una medición de p95 dependiente de la carga de la máquina. En este equipo
  local dio 57,8–93,1 ms (límite 50 ms) y se deseleccionó; no toca el diff de
  HU-31 y el run de CI del PR original la registró verde.

## 6. Cierre

AC1–AC4 cubiertos, sin regresiones en las 435 pruebas Python ejecutadas ni en las
51 de Vitest, contratos y tipos en sincronía. PR #130 fusionado; las observaciones
de revisión se atienden en el PR de corrección de §7.

## 7. Correcciones post-revisión de #130

| Comentario | Corrección | Evidencia |
| --- | --- | --- |
| Bloqueante: el proxy de Vite no cubría `/v1` | Proxy reducido a `/v1` | `frontend/vite.config.ts`, `frontend/tests/viteProxy.test.ts` |
| `HEALTHCHECK` consultaba `/health` | Consulta `/v1/health` | `Dockerfile` |
| AC1 dependía de seguir redirecciones | Condición documentada con `curl -L` y `follow_redirects=True` | `docs/versionado-api.md`, `README.md`, `CONSTITUTION.md` |
| `Deprecation` citada como RFC 8594 y con valor `true` | RFC 9745 con fecha `@1795564800`; `Sunset` sigue en RFC 8594 | `src/m2_cad/api.py`, `docs/versionado-api.md`, `tests/test_hu31_api_v1.py` |
| `"/generar"` inalcanzable en el manejador de 422 | Conjunto reducido a `/v1/generar` | `src/m2_cad/api.py`, `test_regresion_entrada_invalida_sigue_registrandose` |
| `Sunset` fijo acortaba el plazo con el retraso | `M2_SUNSET_RUTAS_PLANAS` configurable | `.env.example`, `docs/versionado-api.md`, `plan.md` |
| `_redirigir_a_v1` no contemplaba `root_path` | Destino construido con `root_path` | `src/m2_cad/api.py`, `test_ac1_redireccion_respeta_root_path` |

PR de corrección: [#138](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/138).
