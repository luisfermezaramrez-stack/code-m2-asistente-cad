# Plan de implementación · HU-32 (SPEC-033)

- **Rama**: `feature/hu-32-costo-limites-idempotencia` (creada desde `origin/main`).
- **Base**: `main` es la única rama de integración. PR #130 (HU-31) sigue abierto;
  este trabajo no depende de `/v1`. Si HU-31 se fusiona primero, se resuelve el
  solapamiento de `api.py` y se regeneran contrato/tipos en el merge.
- **Orden**: spec → plan → tareas → código → pruebas → documentación → PR.

## Objetivo

Cerrar AC1–AC4 sin cambiar el comportamiento de `/generar` cuando no hay topes ni
`Idempotency-Key` (RNF-2). Ninguna solicitud rechazada por límite o por reintento
idempotente debe llegar al modelo pagado.

## Decisiones de diseño

1. **Estado en proceso.** `ControlUso` vive en memoria con `threading.Lock` y se
   inyecta por `Depends(obtener_control_uso)`. El despliegue actual corre con
   `--workers 1`; si se escala, el plan de migración es sustituir el estado por un
   almacén compartido (Redis) sin cambiar la interfaz del controlador.
2. **Identidad de sesión.** Se toma `X-Session-ID` (recortado, máx. 128 chars); si
   no viene, se usa `request.client.host`, y como último recurso `"anonimo"`. No
   se introduce autenticación (fuera de alcance, SPEC-054) ni se guarda IP en el
   registro CSV.
3. **Configuración por entorno** (valores por defecto desactivan el control):
   - `M2_LIMITE_SOLICITUDES_VENTANA` (entero ≥ 0; `0` = sin límite).
   - `M2_VENTANA_SEGUNDOS` (entero ≥ 1; por defecto `60`).
   - `M2_PRESUPUESTO_DIARIO_USD` (float ≥ 0; `0` = sin presupuesto).
   - Los precios por millón de tokens se reutilizan de `MLFLOW_PRECIO_ENTRADA` y
     `MLFLOW_PRECIO_SALIDA` a través de `seguimiento.Configuracion`.
   - El día es UTC natural (`date`), no una ventana móvil de 24 h.
4. **Errores tipados.** `LimiteVentanaExcedido` y `PresupuestoExcedido` devuelven
   `429` con `X-Limite-Tipo: ventana|presupuesto` y `Retry-After` cuando aplica;
   `ConflictoIdempotencia` devuelve `409`. El error de capacidad de 128 trabajos
   se conserva con su `503` (RNF-3) y se distingue por clase de error.
5. **Orden de comprobación.** La idempotencia se evalúa *antes* del presupuesto:
   un reenvío válido debe devolver la generación original aunque el presupuesto
   ya se haya agotado. Para una clave nueva se reserva la entrada de forma
   atómica, se reserva cuota de ventana y, si la cuota falla, se libera la
   reserva idempotente. La ventana se cuenta antes de crear el trabajo, de modo
   que un rechazo no ocupa `GestorTrabajos`.
6. **Idempotencia.** `Idempotency-Key` opcional (máx. 255 chars), con ámbito
   `sesión + texto + transporte` mediante SHA-256. Reenviar la misma clave con
   otro cuerpo o transporte es `409`. La respuesta cacheada incluye el dict JSON
   original y sus cabeceras; para SSE se devuelve el estado terminal disponible
   (o el estado actual del trabajo). Toda respuesta repetida lleva
   `Idempotent-Replay: true`.
7. **Gasto acumulado.** Se suma `seguimiento.costo_usd` en el mismo punto donde
   ya se calcula (`medir_solicitud`), tanto en JSON como en SSE. No se inventa
   costo cuando no hay `usage`. Reintentos y rechazos no suman gasto.
8. **Artefacto consultable.** `GET /uso` devuelve fecha UTC, `costo_usd`, moneda,
   generaciones contabilizadas y presupuesto configurado. Sin PII. Se regeneran
   los tipos TypeScript desde `app.openapi()` (`make api-types`).

## Criterios de aceptación cubiertos

| AC | Prueba prevista |
|----|-----------------|
| AC1 | Presupuesto preagotado → 429 tipado y contador de llamadas al modelo en 0. |
| AC2 | Misma clave dos veces → 1 llamada, mismo `X-Registro-ID`, `Idempotent-Replay`, gasto sin duplicar; clave reutilizada con otro texto → 409. |
| AC3 | K+1 solicitudes de una sesión → la última 429 con `X-Limite-Tipo: ventana`; otra sesión sigue pasando. |
| AC4 | Dos generaciones con `usage` simulado → `GET /uso` devuelve la suma exacta. |

## RNF y verificaciones

- RNF-1: procesador y `usage` simulados; sin red, API key ni GPU.
- RNF-2: las pruebas existentes de `/generar` siguen verdes sin cabeceras nuevas.
- RNF-3: se conserva el test de capacidad 128 → 503.
- `ruff check` + `ruff format --check`, `pytest` con cobertura ≥ 70 %,
  `api-types-check` y `make check`.

## Fuera de alcance

Autenticación/cuentas, facturación, almacenamiento compartido entre workers,
caché/reintentos del LLM (SPEC-026) y cambios al contrato congelado de HU-31.
