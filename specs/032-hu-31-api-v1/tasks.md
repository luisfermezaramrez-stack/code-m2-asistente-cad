# HU-31 — Seguimiento de tareas

## Fase 1 — Análisis y planificación
- [x] Revisar SPEC-032 y los criterios AC1–AC4, RF-1–RF-5 y RNF-1–RNF-2.
- [x] Inventariar las rutas planas y sus usos en API, scripts, frontend y pruebas.
- [x] Decidir el mecanismo de redirección 307 con cabeceras de deprecación.
- [x] Definir la ubicación y el formato del contrato congelado.
- [x] Redactar `plan.md`.

## Fase 2 — Implementación
- [x] Crear `APIRouter(prefix="/v1")` y migrar todas las rutas API al router.
- [x] Registrar redirecciones planas fuera del schema con 307 y cabeceras de deprecación.
- [x] Ajustar `registrar_entrada_invalida` para aceptar `/generar` y `/v1/generar`.
- [x] Fijar `info.version = "1.0.0"`.
- [x] Crear `src/m2_cad/contrato_api.py` con carga y comparación del contrato.
- [x] Generar `contracts/openapi-v1.json` desde `app.openapi()`.
- [x] Redactar `docs/versionado-api.md` con plazo de 90 días y mecanismo de anuncio.
- [x] Migrar `frontend/src/api.ts` y `frontend/src/useGeneration.ts` a `/v1`.
- [x] Regenerar `frontend/src/generated/api.ts` con el generador de SPEC-028.
- [x] Migrar `scripts/smoke_hu07.py` y `scripts/verify_hu15_deployment.py` a `/v1`.
- [x] Actualizar pruebas existentes que inspeccionan paths del OpenAPI.
- [x] Documentar en `README.md`, `CONSTITUTION.md` y `specs/README.md`.

## Fase 3 — Pruebas automatizadas
- [x] AC1: cliente viejo y cliente `/v1` obtienen el mismo resultado (JSON, consulta, descarga y SSE).
- [x] AC1: redirección 307 con `Deprecation`, `Sunset` y `Link`.
- [x] AC2: `validar_contrato` falla al quitar un campo sin subir versión.
- [x] AC3: 100 % de los paths publicados empiezan con `/v1`.
- [x] AC4: política de deprecación documentada con plazo y anuncio.
- [x] Regresión de health/ready, SSE, descargas, SPA y 404 JSON.
- [x] Ruff, formato, Pytest completo, cobertura ≥ 70 %, api-types-check y Vitest.

## Fase 4 — Entrega
- [x] Crear `evidence.md` con resultados verificables y limitaciones.
- [x] Revisar el diff, hacer commit y publicar la rama.
- [x] Abrir Pull Request hacia `main` y solicitar revisión.

## Criterios de cierre
- AC1: 0 regresiones funcionales para clientes de rutas planas.
- AC2: cualquier cambio de schema sin subir versión falla en CI.
- AC3: todas las rutas API del OpenAPI publicado usan `/v1`.
- AC4: plazo y anuncio de deprecación documentados y verificables.
