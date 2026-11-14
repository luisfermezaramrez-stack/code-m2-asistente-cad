# SPEC-013 · HU-06 — Plan técnico de la API FastAPI

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #16). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-013
- **Historia**: #6
- **Responsable**: Juan Camilo Pérez (API); registro: Luis Meza (SPEC-004)
- **Rama**: `feature/hu-06-fastapi`
- **PR**: #16, fusionado 2026-11-10 (`3aab5f4`); archivos: `src/m2_cad/api.py` (+62 −5),
  `tests/test_api.py` (+121)
- **Estado**: Implementada
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Diseño técnico (alcance del PR #16)

Un único módulo `src/m2_cad/api.py` con:

- `app = FastAPI(title="M2 CAD Assistant API", version="0.1.0")`.
- `SolicitudGenerar(BaseModel)`: campo `texto` con `Field(min_length=1, max_length=1000)`
  y un `field_validator` que recorta espacios y rechaza el texto vacío tras el recorte.
- `health()` en `GET /health` → `{"status": "ok"}`.
- `procesador_no_disponible(texto)`: lanza `HTTPException(503)`.
- `obtener_procesador()`: dependencia que devuelve el procesador en uso.
- `generar(solicitud, procesador=Depends(obtener_procesador))` en `POST /generar`:
  devuelve `procesador(solicitud.texto)`.

## Decisiones

| Decisión | Porqué |
|---|---|
| Inyección del procesador con `Depends` | El pipeline (HU-04) y el registro aún no existían; permite probar 200/declinación con dobles vía `app.dependency_overrides` sin GPU ni CAD. |
| 503 como procesador por defecto | Falla explícita y honesta en vez de una respuesta simulada en producción. |
| Validación con Pydantic + recorte | El 422 lo produce FastAPI sin código propio; el validador cubre el caso «solo espacios», que `min_length` no detecta. |
| Límite de 1000 caracteres | Lo fija AC1. |
| Respuesta `dict[str, str]` | Contrato mínimo hasta conocer la salida del pipeline. |

## Contratos (PR #16)

| Método y ruta | Entrada | Respuestas |
|---|---|---|
| `GET /health` | — | `200 {"status": "ok"}` |
| `POST /generar` | `{"texto": str}` (1–1000, no solo espacios) | `200` dict del procesador · `422` validación · `503 {"detail": "El pipeline CAD aún no está disponible."}` |

## Evolución posterior (fuera del PR #16)

Verificado con `git log -- src/m2_cad/api.py`:

- `9168456` (2026-11-09, HU-06 L. Meza): registro de cada `POST /generar` (SPEC-004).
- `a0084b6` (2026-11-10, HU-04): procesador real `procesar_con_pipeline`; declinación
  como `422` (`DeclinacionSolicitud`).
- `25d397d` (2026-11-13, HU-14): planificación directa en español con DeepSeek; el 503
  ahora indica que falta `DEEPSEEK_API_KEY`.
- `72f9948` (2026-11-13, HU-16): una corrida MLflow por solicitud.
- `4d64ee7` (2026-11-13, HU-15, PR #46): SSE, `GET/DELETE /generaciones/{id}` y
  descargas `GET /generaciones/{id}/archivos/{formato}`.

El módulo pasó de 23 a 181 sentencias; los contratos de `GET /health` y la validación
de `POST /generar` se mantienen.

## Riesgos

- **Declinación 200 vs 422**: AC1 pide 200; el comportamiento actual con el pipeline
  real es 422. Un cliente que siga AC1 al pie de la letra fallará.
- **Latencia de `/health` sin prueba**: AC2 no está fijado por ninguna prueba.
- **Cobertura repartida**: `test_api.py` aislado cubre 66 % del módulo actual; borrar
  otras suites bajaría la cobertura por debajo de AC5.

## Alternativas descartadas

No hay registro escrito de alternativas en el PR #16 ni en el issue #6. No se
documentan alternativas que no consten.

## Estrategia de pruebas

- `TestClient` en proceso, sin red ni GPU; importaciones dentro de cada prueba.
- Casos parametrizados para `""`, `"   "` y 1001 caracteres (422).
- Dobles del procesador con `app.dependency_overrides[obtener_procesador]` para éxito
  con archivos CAD simulados y para declinación, limpiando el override al final.
- Prueba explícita del 503 con el procesador por defecto.
- Cobertura: `uv run pytest tests/test_api.py --cov=m2_cad.api -q`.
