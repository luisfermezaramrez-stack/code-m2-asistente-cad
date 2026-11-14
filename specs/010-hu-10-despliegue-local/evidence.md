# SPEC-010 · HU-10 — Evidencia del despliegue local

- **Fecha**: 2026-11-13 · **Rama**: `feature/hu-10-despliegue-local`
- **Entorno**: Linux, Docker Compose 5.6.0, sin GPU · **Modelo**: DeepSeek `deepseek-v4-pro` por API
- **Datos crudos**: [`evidencia/`](./evidencia/) (`humo.*` para AC4, `latencia.*` para AC3)

## AC1 — Arranque con un solo comando

`docker compose up -d --no-build` (equivalente a `make up` en segundo plano) con `.env`
que solo define `DEEPSEEK_API_KEY`: `/health` respondió 200 a los **3 s**.

```text
m2-cad | Up 27 seconds (healthy) | 127.0.0.1:8000->8000/tcp
mlflow | Up 27 seconds           | 127.0.0.1:5000->5000/tcp
```

> **Limitación**: la imagen ya estaba construida en el equipo. El rebuild completo
> (`docker compose up --build`) falló en este host por memoria agotada
> (`ResourceExhausted: cannot allocate memory` en `uv sync`, con 2,8 GB libres y swap
> lleno). No es un defecto del proyecto, pero el arranque en una máquina realmente limpia
> no se repitió en esta sesión; la CI construye la imagen en cada PR.

## AC2 — Acceso local

| URL | Resultado |
| --- | --- |
| `http://localhost:8000/` | 200, contiene `<div id="app">` (SPA Vue) |
| `http://localhost:8000/health` | 200 `{"status":"ok"}` |
| `http://localhost:8000/docs` | 200 (OpenAPI) |
| `http://127.0.0.1:5000/` | 200 (UI de MLflow) |

Ambos puertos se publican solo en `127.0.0.1` (RNF-3). Antes de HU-10 la API publicaba
`8000:8000` en todas las interfaces; se corrigió en `docker-compose.yml`.

## AC4 — Prueba de humo (5 solicitudes, una por familia)

`uv run python scripts/smoke_deploy.py --n 5` → **5/5 válidas**.

| id | familia | HTTP | resultado | latencia |
| --- | --- | --- | --- | --- |
| HU02-P01 | plate | 200 | pieza | 13,0 s |
| HU02-P06 | sheet_bracket | 200 | pieza | 3,9 s |
| HU02-P11 | adapter | 200 | pieza | 3,4 s |
| HU02-P16 | flange | 200 | pieza | 10,8 s |
| HU02-P21 | spacer | 200 | pieza | 3,5 s |

La primera solicitud incluye la carga diferida del núcleo CAD (cadquery/OCP).

## AC3 — Latencia (40 solicitudes del banco HU-02, ≥ 30)

`uv run python scripts/smoke_deploy.py --n 40`, secuencial, medido del lado del cliente:

| Métrica | Valor |
| --- | --- |
| Solicitudes | 40 (30 positivas, 10 fuera de alcance) |
| p50 | **3,4 s** |
| p90 | **4,5 s** (umbral ≤ 60 s ✅) |
| Máximo | 7,6 s |
| Piezas entregadas | 30/30 positivas |
| Declinaciones con motivo | 9/10 negativas |

**Hallazgo (no bloquea AC3):** `HU02-N03` («certificado RETIE») devolvió 422 con
`program needs a non-empty 'parts' list`. El modelo respondió un programa vacío en lugar
de declararlo fuera de catálogo, así que el verificador lo rechazó: no se entregó ninguna
pieza, pero tampoco la declinación explícita (`Pieza declinada: …`). El script lo cuenta
como `error` a propósito. Es una cuestión de calidad del modelo y del prompt (HU-14), no
del despliegue.

## AC5 — Apagado y documentación

`make down` eliminó `m2-cad`, `mlflow` y la red; `docker compose ps -a` y
`docker ps --filter name=code-m2-asistente-cad` quedaron vacíos. El README documenta
requisitos, arranque, URLs, prueba de humo, puertos y apagado en
«Despliegue local con Docker Compose (HU-10)».
