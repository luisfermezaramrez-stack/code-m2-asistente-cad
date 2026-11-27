# SPEC-052 — HU-51 · Plan técnico

Issue: #111 · Rama: `feature/hu-51-panorama-metricas` · Destino PR: `main`.

## Decisiones

1. **Fuente única (S2)**: las cifras salen de las corridas de MLflow del experimento de
   generación. No se crea almacén ni caché propia: `metricas.leer_corridas` usa el mismo
   `Configuracion`/`MlflowClient` de `seguimiento.py` y `resumir_corridas` es una función
   pura sobre los datos ya registrados (estado, causa de declinación, latencia, costo,
   familia y versión de prompt).
2. **Ventana (S1)**: `horas` como parámetro de consulta, por defecto 24, entre 1 y 720. Se
   filtra por `start_time` de la corrida y se devuelve `desde`/`hasta` explícitos para que la
   UI y MLflow hablen del mismo intervalo.
3. **Estado degradado (AC2, S6)**: si el seguimiento está desactivado o MLflow falla, el
   endpoint responde **200** con `disponible: false`, un `motivo` fijo en español y los
   agregados vacíos; nunca 500. El `motivo` **no** incluye texto de la excepción ni de la URI
   (rutas, hosts y credenciales quedan sólo en el log, redactados), y la UI muestra el motivo
   con un botón para reintentar, también cuando falla la petición.
4. **Sin PII (S7)**: el panorama agrega por causa (`declinaciones_por_causa`) y por familia
   (`entregadas_por_familia`); no devuelve textos de solicitud, nombres de usuario ni
   identificadores de corrida más allá del enlace a MLflow. `familia` y `prompt` se normalizan
   en cada fila para trazabilidad; `prompt` hoy no se agrega.
5. **Enlace a MLflow (S4, AC3)**: `mlflow_ui` sale de `MLFLOW_UI_URL` (por defecto
   `http://127.0.0.1:5000`), que es la UI que el repo ya levanta con `make mlflow`.
6. **UI sin librería nueva (S3)**: una vista (`MetricsView.vue`) con tablas y cifras, más una
   entrada de navegación y una ruta. No se añade ninguna dependencia de gráficos.
7. **Colección de huérfanas**: nada de esto toca `/generar`, el prompt ni el registro.

## Interfaces congeladas

`src/m2_cad/metricas.py`

```python
class SeguimientoNoDisponible(RuntimeError)
def lectura(corrida: dict) -> dict           # normaliza una fila de search_runs
def leer_corridas(configuracion, *, desde: datetime, hasta: datetime) -> list[dict]
def resumir_corridas(corridas: list[dict], *, desde, hasta, motivo: str | None = None) -> dict
def panorama(configuracion, *, horas: int) -> dict   # agrega o degrada, nunca lanza
```

`GET /v1/metricas` → `PanoramaMetricas` (typed) con `disponible`, `motivo`, `desde`, `hasta`,
`solicitudes`, `entregadas`, `declinadas`, `errores`, `declinaciones_por_causa`,
`latencia_media_ms`, `costo_usd`, `mlflow_ui`, `generado_en`.

## Hallazgos de la revisión nativa y su corrección

- **Lectura completa**: `leer_corridas` filtra en el servidor por `attributes.start_time`,
  ordena por inicio descendente y **pagina** por `token` con página de 1.000: nada de topes
  silenciosos que acortaran las cifras.
- **Plazo del backend**: la lectura corre con `MLFLOW_HTTP_REQUEST_TIMEOUT` fijado a
  `ESPERA_BACKEND_S` (5 s) y lo restaura al salir, para que un MLflow colgado degrade en vez
  de bloquear el handler.
- **Una sola ventana**: `_en_ventana` es el único predicado y lo usa sólo `resumir_corridas`;
  el lector ya no vuelve a filtrar en memoria.
- **Sin helper privado**: `seguimiento.preparar_entorno` es la puerta pública que usa el
  módulo de métricas.
- **Enlace seguro**: la vista sólo pinta el enlace a MLflow si `mlflow_ui` empieza por
  `http://` o `https://`.

## Pruebas

- `tests/test_metricas.py`: agregación pura (totales, causas, media de latencia, suma de
  costo, filtrado por ventana, corridas sin métricas no rompen); degradado con seguimiento
  inactivo y con cliente que falla; sin PII en el resultado; endpoint con `TestClient`
  (200 con datos desde un file store temporal, 200 degradado, 422 con `horas` fuera de rango).
- `frontend/tests/Metrics.test.ts`: la vista muestra el costo acumulado y enlaza a MLflow, y
  con `disponible: false` muestra el motivo sin romperse.
