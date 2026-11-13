# HU-16 — Plan técnico del seguimiento con MLflow

## 1. Objetivo

Añadir observabilidad de experimentos al pipeline sin cambiar su comportamiento
funcional: cada solicitud y cada corrida del banco se registran en MLflow con
parámetros, métricas y artefactos, y la generación sigue funcionando cuando el
servidor de seguimiento no está disponible.

La pieza entregada al usuario no cambia; cambia lo que el equipo puede medir después.

## 2. Arquitectura

Flujo por solicitud:

1. Gradio envía el texto a FastAPI (`POST /generar`).
2. `api.procesar_con_pipeline` abre una corrida en MLflow (experimento
   `m2-cad-generacion`).
3. El pipeline genera el programa DSL, lo verifica y construye la pieza.
4. La corrida registra params, métricas y artefactos, y cierra con
   `estado=entregada|declinada|error`.
5. La respuesta HTTP se emite con el resultado de siempre; el seguimiento es
   best-effort.

Flujo del banco (`make bench`):

1. `banco.main` abre una corrida padre por modelo con los precios de entrada/salida.
2. Cada caso abre una corrida hija (`evaluar_caso`).
3. El resumen (`resumir`) se registra como métricas de la corrida padre.

### Componentes

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Seguimiento | `src/m2_cad/seguimiento.py` (nuevo) | Interfaz con MLflow, contexto de corrida y modo no-op |
| API | `src/m2_cad/api.py` | Abrir/cerrar la corrida por solicitud y capturar el error |
| Pipeline | `src/m2_cad/pipeline.py` | Exponer `generar_pieza` con contexto opcional y datos medibles |
| Banco | `src/m2_cad/banco.py` | Corrida padre por modelo y una hija por caso |
| Registro | `src/m2_cad/registro.py` | Sanitización de PII reutilizada por el seguimiento |
| Despliegue | `docker-compose.yml` | Servicio `mlflow` con volumen persistente |
| Comandos | `Makefile` | `make mlflow` (servidor solo) |

## 3. Modelo de seguimiento

### Experimento `m2-cad-generacion` (una corrida por solicitud)

| Campo | Tipo | Valor |
|---|---|---|
| `modelo` | param | `deepseek-v4-pro` o el GGUF heredado |
| `version_modelo` | param | versión/fecha reportada por el proveedor o digest del GGUF |
| `familia` | param | familia del catálogo o `desconocida` si declina antes de decidirla |
| `temperatura` | param | temperatura efectiva de la llamada |
| `latencia_ms` | metric | extremo a extremo de la solicitud |
| `tokens_entrada` / `tokens_salida` | metric | uso reportado por el proveedor |
| `costo_usd` | metric | tokens × precio configurado (0 si no aplica) |
| `verificacion_ok` | metric | 1 si `/dsl/check` y la caja pasan; 0 si no |
| `solicitud_id` | tag | identificador de la corrida, correlacionado con `registro.csv` |
| `estado` | tag | `entregada` \| `declinada` \| `error` |
| `motivo_declinacion` / `error` | tag | motivo de la declinación o clase de la excepción |
| `programa.json`, `step`, `glb`, `bom_csv` | artifacts | programa DSL y entregables de `outputs/<uuid>/` |

### Experimento `m2-cad-banco` (una corrida padre por modelo)

| Campo | Tipo | Valor |
|---|---|---|
| `modelo`, `precio_entrada`, `precio_salida` | params | configuración de la corrida |
| `n_casos` | param | tamaño del banco |
| `acierto`, `acierto_positivas`, `acierto_negativas` | metric | resumen del banco |
| `dsl_check_ok_total` | metric | casos que pasan `/dsl/check` |
| `latencia_media_s`, `tokens_entrada`, `tokens_salida`, `costo_usd` | metric | resumen medido |
| `caso` (hija) → `acierto`, `dsl_check_ok`, `error_relativo_pct` | metrics | resultado por caso |

## 4. Configuración

Variables de entorno nuevas (documentadas en el README y en `.env.example`):

| Variable | Valor local predeterminado | Función |
|---|---|---|
| `MLFLOW_TRACKING_URI` | `file:./mlruns` | Destino del seguimiento |
| `MLFLOW_EXPERIMENT_NAME` | `m2-cad-generacion` | Experimento de solicitudes |
| `MLFLOW_EXPERIMENT_BANCO` | `m2-cad-banco` | Experimento del banco |
| `MLFLOW_TRACKING_ENABLED` | `1` | `0` desactiva el seguimiento (modo no-op) |
| `MLFLOW_PRECIO_ENTRADA` / `MLFLOW_PRECIO_SALIDA` | `0` | Precio por millón de tokens para `costo_usd` |

En Compose, `m2-cad` apunta a `http://mlflow:5000`; en local, al file store
`./mlruns` (las pruebas usan `tmp_path/mlruns`).

## 5. Despliegue mediante Docker Compose

### Servicio `mlflow`

- Imagen oficial fija (`ghcr.io/mlflow/mlflow:v2.x`); la versión exacta se fija en el
  commit de implementación.
- Comando: `mlflow server --backend-store-uri sqlite:////mlflow/mlflow.db --artifacts-destination /mlflow/artifacts --host 0.0.0.0 --port 5000`.
- Puerto `5000:5000`, publicado solo en `127.0.0.1` en local.
- Volumen nombrado sobre `/mlflow` para conservar base y artefactos.
- Sin GPU, sin secretos y sin credenciales.

### Servicios existentes

`m2-cad` recibe `MLFLOW_TRACKING_URI=http://mlflow:5000` y `depends_on: mlflow` con
espera tolerante: si MLflow tarda en arrancar, la generación no falla (AC6).

### Artefactos

`outputs/` sigue siendo el almacén de entregables del usuario; MLflow guarda **copias**
como artefactos de la corrida. Nada en MLflow es fuente de verdad de la pieza.

## 6. Seguridad y controles

- La UI de MLflow no tiene autenticación: nunca se publica fuera de `127.0.0.1` ni de la
  red interna de Compose.
- El texto de la solicitud pasa por `_sanitizar` de `registro.py` antes de entrar como
  param o tag (AC5).
- Los artefactos se leen de `outputs/<uuid>/` con la misma comprobación de ruta que la
  interfaz (`archivo_seguro`), nunca rutas arbitrarias.
- Prohibido registrar claves (`DEEPSEEK_API_KEY`) o el cuerpo completo de la respuesta
  del proveedor.
- `mlruns/`, `mlflow.db` y los artefactos volcados quedan en `.gitignore`.

## 7. Estrategia de pruebas

### Pruebas automatizadas (offline, `tmp_path/mlruns`)

- El modo desactivado no abre corridas y no altera el resultado.
- Una solicitud exitosa produce una corrida con los params, métricas y artefactos de AC2.
- Una declinación produce `estado=declinada` con motivo (AC3).
- Un fallo técnico produce `estado=error` sin romper la respuesta HTTP (AC3).
- Niguna corrida queda en `RUNNING` al cerrar.
- El texto registrado no contiene correos ni nombres declarados (AC5).
- Servidor inalcanzable: la generación concluye y se emite una advertencia (AC6).
- El banco abre una corrida padre y N hijas con las métricas del resumen (AC4).
- La versión de modelo queda ligada a la corrida (AC7).

### Pruebas de despliegue

```bash
docker compose config --quiet
docker compose up -d mlflow
curl -I http://127.0.0.1:5000
```

### Pruebas manuales

- Dos corridas del banco (DeepSeek y Gemma heredado) comparadas en la UI de MLflow.
- Captura de la tabla de corridas y del detalle con artefactos → `evidence.md`.

## 8. Criterios de cierre

1. `make check` y `make cov` en verde (cobertura ≥ 70 %).
2. Las pruebas de MLflow corren sin red y sin GPU.
3. `docker compose up mlflow` sirve la UI en `127.0.0.1:5000`.
4. Una solicitud real aparece en la UI con artefactos descargables.
5. Dos modelos comparados en el experimento `m2-cad-banco`.
6. `CONSTITUTION.md` (§0 estado, §3 stack, §4 estructura, §9 historial) actualizado en el
   mismo commit.
7. `evidence.md` con capturas y comandos reproducibles.
