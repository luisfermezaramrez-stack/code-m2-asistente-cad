# HU-16 — Seguimiento de experimentos con MLflow

- **Responsable**: Luis Meza
- **Rama**: `feature/hu-16-mlflow`
- **Issue**: #45

## Objetivo

Instrumentar el pipeline CAD con **MLflow** para que cada solicitud y cada corrida
del banco de pruebas quede registrada como una corrida reproducible: parámetros del
modelo, métricas (latencia, tokens, costo, resultado de la verificación) y artefactos
(programa DSL, STEP, GLB, CSV). Con eso se puede comparar `deepseek-v4-pro` contra la
línea base Gemma sin revisar casos a mano, y ligar cada evidencia a la versión exacta
del modelo que la produjo.

## Tecnologías

- MLflow (cliente `mlflow-skinny`, servidor en imagen oficial fija)
- SQLite como backend de seguimiento (`mlflow.db`) y `mlruns/` para artefactos
- Docker Compose (nuevo servicio `mlflow`)
- FastAPI, pipeline existente y runner del banco (`m2_cad.banco`)
- `uv` para la dependencia, `pytest` para las pruebas

## Criterios de aceptación

### AC1 — Servidor de seguimiento en Docker Compose

`docker compose up` levanta un servicio `mlflow` con la UI accesible en
`http://127.0.0.1:5000`, backend `sqlite:///mlflow.db` y los artefactos en un volumen
persistente. Se puede levantar solo con `make mlflow`. Sin GPU ni red externa.

### AC2 — Una corrida por solicitud

Cada solicitud procesada crea exactamente **una** corrida en el experimento
`m2-cad-generacion` con:

- **params**: `modelo`, `version_modelo`, `familia`, `temperatura`
- **metrics**: `latencia_ms`, `tokens_entrada`, `tokens_salida`, `costo_usd`,
  `verificacion_ok` (0/1)
- **tags**: `solicitud_id`, `estado` (`entregada` | `declinada` | `error`)
- **artifacts**: `programa.json` siempre; `step`, `glb` y `bom_csv` cuando la pieza se
  construye

### AC3 — Declinaciones y errores con motivo

Una pieza declinada cierra su corrida con `estado=declinada` y el motivo en el tag
`motivo_declinacion`. Un fallo técnico la cierra con `estado=error` y la clase de la
excepción en el tag `error`. Ninguna corrida queda en `RUNNING` al responder la
solicitud.

### AC4 — Banco comparativo entre modelos

`make bench` abre una corrida padre por modelo y una corrida hija por caso, con
`acierto` (0/1), `dsl_check_ok` (0/1) y `error_relativo_pct`. El resumen del banco
—acierto, latencia media, tokens y costo— queda como métricas de la corrida padre, de
modo que dos modelos se comparan en la UI de MLflow sin abrir el CSV.

### AC5 — Exclusión de PII (Ley 1581 de 2012)

Todo texto que se registre como parámetro, tag o artefacto pasa por la misma
sanitización de `src/m2_cad/registro.py`. Ninguna corrida contiene correos ni nombres
declarados por el usuario; se verifica con el mismo corpus del AC4 de HU-06.

### AC6 — Degradación segura

Si el servidor de MLflow no responde o si `MLFLOW_TRACKING_ENABLED=0`, la generación
concluye igual y el fallo del seguimiento se emite como advertencia en el log. No hay
reintentos bloqueantes ni excepción propagada al usuario, y la sobrecarga del
seguimiento es ≤ 50 ms p95 con backend local.

### AC7 — Versiones de modelo registradas

Cada configuración servida (`deepseek-v4-pro` y, en la línea base heredada,
`gemma-4-12b-constraintkit` Q6_K) se registra como versión de modelo con sus
parámetros, y cada corrida queda ligada a esa versión. Desaparece el marcador
`version="desconocida"` del registro.

### AC8 — Pruebas, configuración y evidencia

Las pruebas corren **offline** contra un file store temporal (`tmp_path/mlruns`), sin
red ni GPU, y la cobertura de `src/m2_cad` sigue siendo ≥ 70 %. `mlruns/` y
`mlflow.db` quedan en `.gitignore`, las variables nuevas se documentan en el README, y
`specs/009-hu-16-mlflow/evidence.md` muestra la UI con dos corridas comparadas.

## Integración

- **Pipeline** (`src/m2_cad/pipeline.py`): `generar_pieza` acepta un contexto de
  seguimiento opcional; sin él se comporta exactamente como hoy.
- **API** (`src/m2_cad/api.py`): `procesar_con_pipeline` abre y cierra la corrida por
  solicitud; el registro CSV (`data/registro.csv`) se mantiene como traza ligera.
- **Banco** (`src/m2_cad/banco.py`): `main` crea la corrida padre y `evaluar_caso`
  registra la hija; el contador de tokens ya existente (`ContadorUso`) alimenta las
  métricas.
- **Módulo nuevo**: `src/m2_cad/seguimiento.py` concentra la interfaz con MLflow y el
  modo desactivado (no-op).

## Restricciones

- Una sola corrida por solicitud HTTP; el seguimiento nunca bloquea ni alarga la
  respuesta por encima de lo declarado en AC6.
- Sin autenticación en el servidor de MLflow: escucha en `127.0.0.1` en local y solo en
  la red interna de Compose; nunca se expone a Internet.
- Prohibido versionar `mlruns/`, `mlflow.db` y los pesos del modelo.
- Toda dependencia entra por `uv add`; `pip` y `requirements.txt` siguen prohibidos.
- El seguimiento no sustituye la verificación geométrica determinista (HU-04): es
  observabilidad, no criterio de aceptación de la pieza.
- `CONSTITUTION.md` se actualiza en el mismo commit que el cambio de stack.
