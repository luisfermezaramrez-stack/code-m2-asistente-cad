# HU-31 — Evidencia de cierre (SPEC-032)

- **Fecha:** 2026-11-25
- **Rama:** `feature/hu-31-api-v1`
- **Base:** `origin/main` en `80d7850` (FAST-forward local)
- **PR:** [#130](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/130) (abierta, en revisión)

## 1. Criterios de aceptación

| AC | Verificación | Resultado |
| --- | --- | --- |
| AC1 | `tests/test_hu31_api_v1.py`: mismos JSON, consulta y descarga STEP llamando a `/generar` y a `/v1/generar`; 9 rutas planas responden `307` con `Deprecation`, `Sunset` y `Link`; la query se conserva | ✅ |
| AC2 | `test_ac2_quitar_un_campo_del_esquema_rompe_el_contrato`: eliminar `EstadoTrabajo.estado` de una copia del esquema hace fallar `validar_contrato` con la ruta del campo | ✅ |
| AC3 | `test_ac3_el_openapi_publicado_solo_contiene_v1_y_esta_congelado`: `info.version == "1.0.0"`, todas las claves de `paths` empiezan con `/v1/` y coinciden con `contracts/openapi-v1.json` | ✅ |
| AC4 | `test_ac4_la_politica_de_deprecacion_esta_documentada`: `docs/versionado-api.md` contiene `90 días`, `Deprecation`, `Sunset` y la fecha `Tue, 23 Feb 2027 00:00:00 GMT` | ✅ |

## 2. Comandos y resultados

Ejecutados en macOS x86_64 con el entorno `.venv` existente. Se usa
`uv run --no-sync` en local porque `uv run --locked` intenta reconstruir
`nlopt==2.11.0` en esta arquitectura; CI mantiene `--locked` desde los lockfiles.

```text
$ uv run --no-sync ruff check src tests scripts/verify_hu15_deployment.py \
    scripts/generate_api_types.py scripts/generate_api_contract.py
All checks passed!

$ uv run --no-sync ruff format --check src tests scripts/generate_api_contract.py
44 files already formatted

$ uv run --no-sync python scripts/generate_api_contract.py --check
Contrato OpenAPI v1 actualizado.

$ uv run --no-sync python scripts/generate_api_types.py --check
Tipos OpenAPI actualizados.

$ M2_DOWNLOAD_SECRET=<secreto-efimero-de-64-bytes> \
    uv run --no-sync pytest -q --cov=m2_cad --cov-report=term-missing
431 passed, 26 warnings in 50.07s
TOTAL 1837 stmts, 112 miss, 94% cover
Required test coverage of 70.0% reached. Total coverage: 93.90%

$ npm --prefix frontend test
Test Files  3 passed (3)
Tests       50 passed (50)

$ npm --prefix frontend run typecheck
(no errors)

$ npm --prefix frontend run build
✓ built in 1.04s
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
  planas `307` fuera del esquema y registro de entradas inválidas en ambas rutas.
- `src/m2_cad/contrato_api.py`, `contracts/openapi-v1.json`: contrato congelado
  determinista y comparación con diagnóstico de la primera divergencia.
- `scripts/generate_api_contract.py`, targets `api-contract` y
  `api-contract-check` (incluidos en `make check`).
- `docs/versionado-api.md`, `README.md`, `CONSTITUTION.md`: política de 90 días,
  mecanismo de anuncio y regla de cambios incompatibles → `/v2`.
- SPA, scripts y evaluador HTTP consumen `/v1`; tipos TypeScript regenerados
  con el generador de SPEC-028 (sin edición manual).
- `tests/test_hu31_api_v1.py` más ajustes de pruebas existentes que inspeccionan
  paths del OpenAPI o simulan el transporte HTTP.

## 5. Limitaciones

- No se publica `/v2` ni autenticación; ambas decisiones quedan fuera de alcance.
- Las redirecciones planas son temporales y se retirarán tras el `Sunset`.
- El nombre del tipo generado cambia por el prefijo `/v1`; `frontend/src/api.ts`
  conserva el alias público `Job` para no propagar el renombrado al componente.
- El build del frontend avisa de un chunk > 500 kB (`GlbViewer`), advertencia
  preexistente no introducida por esta HU.

## 6. Cierre

AC1–AC4 cubiertos, sin regresiones en las 431 pruebas Python ni en las 50 de
Vitest, contratos y tipos en sincronía. Pendiente únicamente la revisión y
fusión del PR.
