# HU-16 — Evidencia del seguimiento con MLflow

Rama `feature/hu-16-mlflow` · issue #45 · responsable Luis Meza · fecha 2026-11-13.
Sin commits de evidencia: la rama queda para revisión del usuario.

## AC8 — Pruebas, cobertura e higiene

```bash
make check   # Ruff (E, F, I, B) + pytest
make cov     # pytest --cov=src/m2_cad
```

Salida observada (2026-11-13):

```text
233 passed, 21 warnings in 17.22s
src/m2_cad/seguimiento.py   170 stmts  21 miss  88%
TOTAL                       843 stmts  37 miss  96%
Required test coverage of 70.0 % reached. Total coverage: 95.61 %
```

Las pruebas nuevas corren **offline** contra `tmp_path/mlruns` (file store temporal, sin
red ni GPU):

| Archivo | Cubre |
|---|---|
| `tests/test_seguimiento.py` (9) | módulo: params/métricas/tags/artefactos, sanitización, no-op, servidor caído, `costo_usd`, versión de modelo, gate de sobrecarga p95 |
| `tests/test_api_seguimiento.py` (7) | una corrida por solicitud, `estado=entregada/declinada/error`, artefactos, `FINISHED`, fin de `version="desconocida"`, excepción no HTTP que no bloquea la siguiente, ligadura a la versión de modelo |
| `tests/test_banco_seguimiento.py` (5) | corrida padre con el resumen, hija por caso, versión de modelo registrada, interrupción que cierra la padre, restauración de `llm.chat` |
| `tests/test_pipeline.py` (1 nueva) | `programa.json` sanitizado (AC5) |

`mlruns/`, `mlflow.db` y `mlflow-artifacts/` quedan en `.gitignore`; las variables nuevas
están documentadas en el README (§ «Seguimiento de experimentos» y tabla de variables).

## AC1 — Servidor de seguimiento en Compose

```bash
docker compose config --quiet   # exit 0
make mlflow                     # docker compose up -d mlflow
curl -I http://127.0.0.1:5000
```

Servicio `mlflow` con `ghcr.io/mlflow/mlflow:v3.18.0`, backend
`sqlite:////mlflow/mlflow.db`, artefactos en `/mlflow/artifacts` (volumen `mlflow-datos`)
y puerto publicado solo en `127.0.0.1:5000`. `m2-cad` usa `MLFLOW_TRACKING_URI=http://mlflow:5000`.

Salida observada (2026-11-13):

```text
--- UI ---
HTTP 200 en 0.011037s
--- estado ---
NAME                             IMAGE                           SERVICE   STATUS        PORTS
code-m2-asistente-cad-mlflow-1   ghcr.io/mlflow/mlflow:v3.18.0   mlflow    Up 15 seconds 127.0.0.1:5000->5000/tcp
```

Prueba de humo cliente → servidor real (`MLFLOW_TRACKING_URI=http://127.0.0.1:5000`):

```text
corrida=774c39bf902e43eaa64f2ab82ba4f077 activa=False fallos=0
estado FINISHED | tag entregada | familia spacer
artefactos ['programa.json']
```

UI local: <http://127.0.0.1:5000/#/experiments/1> (`make down` detiene el servicio).
La captura de pantalla de la UI y la comparación de dos modelos reales quedan como
evidencia manual pendiente (requieren gastar tokens del modelo).

## AC2/AC3 — Una corrida por solicitud

```bash
uv run pytest tests/test_api_seguimiento.py -q     # 5 passed
```

Lo que verifican:

- `params`: `modelo`, `version_modelo`, `familia`, `temperatura`.
- `metrics`: `latencia_ms`, `tokens_entrada`, `tokens_salida`, `costo_usd`, `verificacion_ok`.
- `tags`: `solicitud_id` (uuid correlacionado con `data/registro.csv`), `estado`
  (`entregada` | `declinada` | `error`), `motivo_declinacion` o `error` (clase).
- `artifacts`: `programa.json` (escrito por el pipeline en `outputs/<uuid>/`), más
  `pieza.step`, `pieza.glb` y `pieza.csv` cuando la pieza se construye.
- Toda corrida cierra en `FINISHED`: ninguna queda en `RUNNING` (aserción explícita por
  prueba, incluida la del 503 por falta de `DEEPSEEK_API_KEY`).

## AC4/AC7 — Banco comparativo y versión de modelo

```bash
uv run pytest tests/test_banco_seguimiento.py -q   # 3 passed
```

- Corrida padre `m2-cad-banco` por modelo: params `modelo`, `version_modelo`,
  `precio_entrada`, `precio_salida`, `n_casos`; métricas `acierto`,
  `acierto_positivas`, `acierto_negativas`, `dsl_check_ok_total`, `latencia_media_s`,
  `tokens_entrada`, `tokens_salida`, `costo_usd`.
- Una corrida hija por caso (`HU02-P01`, `HU02-N01`, …) con `acierto`, `dsl_check_ok`,
  `error_relativo_pct` (error relativo del volumen contra la referencia, en %) y
  `latencia_s`.
- La configuración servida se registra una sola vez como versión de modelo
  (`m2-cad-<modelo>`, tag `version_modelo`) ligada a la corrida padre.
- El CSV de registro de la API ya no escribe `version="desconocida"`: usa
  `seguimiento.version_modelo()` (`LLM_MODEL_VERSION` o el id del modelo servido).
- La ruta de **generación** también registra la versión de modelo y deja el tag
  `modelo_registrado` (`m2-cad-<modelo>/vN`) en la corrida: la versión se crea una sola
  vez por `(uri, modelo, versión)` y las solicitudes siguientes la reutilizan
  (`tests/test_api_seguimiento.py::test_solicitud_ligada_a_la_version_de_modelo_registrada`).

Pendiente humano: `make bench IDS=... --precio-entrada ...` con los dos modelos reales
(DeepSeek y la línea base Gemma) para la captura comparada en la UI; gasta tokens.

## AC5 — Exclusión de PII (Ley 1581 de 2012)

Corpus de HU-06 registrado como nombre de corrida, param y tag:

```text
Contacto: juan.perez@example.com para la pieza de 120 mm
Escribime a soporte-cad@unia.edu.co antes de cortar la placa
me llamo Ana López y necesito una brida DN50
```

Resultado:

```text
corridas=3 textos_registrados=33 fugas=0 marcadores=18
AC5 PII fuera del seguimiento: OK
```

Cada texto pasa por `_sanitizar` de `src/m2_cad/registro.py` antes de llegar a MLflow.
Los **artefactos** también: `pipeline.generar_pieza` sanitiza el JSON antes de escribir
`programa.json` (el programa en memoria sigue intacto para construir la pieza), cubierto
por `tests/test_pipeline.py::test_programa_json_escrito_pasa_por_la_sanitizacion`
(RED→GREEN: antes el correo y el nombre del modelo llegaban al archivo sin cambios).

## AC6 — Degradación segura y sobrecarga

`tests/test_seguimiento.py` cubre `MLFLOW_TRACKING_ENABLED=0` (no abre corridas) y un
servidor inalcanzable (`http://127.0.0.1:9`): la corrida queda inactiva, se emite una
advertencia en el log y nada se propaga ni reintenta (timeout 2 s, 0 reintentos HTTP).

Sobrecarga medida con backend local (25 muestras, diferencia contra el modo desactivado):

```text
muestras=25 mediana=15.1 ms p95=19.5 ms max=24.0 ms
AC6 p95<=50ms: OK
```

Gate automatizado: `tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms`
— mide la **diferencia** entre una corrida completa (params, métricas, cierre) y la misma
secuencia en modo no-op, 12 muestras tras calentar, p95 ≤ 50 ms. La primera versión medía
tiempo absoluto y falló en la suite completa por carga de la máquina: la diferencia cancela
ese ruido.
