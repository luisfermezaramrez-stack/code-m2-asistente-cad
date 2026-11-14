# SPEC-010 · HU-10 — Plan técnico del despliegue local

- **ID**: SPEC-010 · **Historia**: #10 · **Responsable**: Juan Camilo Pérez
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## 1. Diseño técnico

El stack ya tiene las piezas; HU-10 las convierte en un despliegue verificable:

```text
navegador ──HTTP──▶ api (uvicorn m2_cad.api:app, :8000)
                       ├─ sirve el build de Vue (mismo origen, HU-15)
                       ├─ POST /generar · GET /health · /docs
                       └─ MLFLOW_TRACKING_URI=http://mlflow:5000
                    mlflow (imagen oficial fija, :5000, sqlite + volumen)
api ──HTTPS──▶ api.deepseek.com (DEEPSEEK_API_KEY desde .env)
```

- `docker-compose.yml` es la fuente única de los servicios `api` y `mlflow`.
- `make up` / `make down` envuelven `docker compose up` / `docker compose down`.
- Prueba de humo y latencia: script nuevo `scripts/smoke_deploy.py` que lee el banco
  (`m2_cad.dataset.read_dataset`), envía N solicitudes a `POST /generar` contra
  `--base-url` (por defecto `http://localhost:8000`) y escribe un CSV con id, familia,
  estado HTTP, resultado y latencia, más el p50/p90 en un JSON.

## 2. Decisiones

| Decisión | Porqué |
| --- | --- |
| Un solo origen (`:8000`) para SPA y API | Lo exige HU-15 AC6; evita CORS en el despliegue y simplifica la demo. |
| MLflow en el mismo `compose` | HU-16 ya lo definió; la demo del M3 necesita la UI viva junto al servicio. |
| Script de humo en Python con `httpx` | `httpx` ya es dependencia; reutiliza el lector del banco y corre con `uv run`. |
| Medir latencia del lado del cliente | Es la latencia que percibe el evaluador, incluida la red hasta DeepSeek. |
| `make up` en primer plano | Los logs quedan visibles durante la demo; `make down` limpia. |

## 3. Contratos

- `GET /health` → `200 {"status": "ok"}` (contrato existente de HU-06, `src/m2_cad/api.py:50`).
- `POST /generar` → contrato existente (HU-06/HU-15); el script no lo modifica.
- `scripts/smoke_deploy.py --base-url URL --n N [--ids ...] --salida DIR` → código de
  salida 0 si todas las solicitudes responden con pieza o declinación; 1 si alguna falla.
- Variables: `DEEPSEEK_API_KEY` (obligatoria), `M2_CORS_ORIGINS`, `MLFLOW_TRACKING_URI`.

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Límite de tasa o latencia variable de DeepSeek | Solicitudes secuenciales y p90 sobre ≥ 30 casos; se reporta el valor medido, no se ajusta. |
| Costo de tokens al medir 30+ solicitudes | Se registra el costo; las pruebas automáticas simulan el modelo. |
| Build de Vue ausente en la imagen | El Dockerfile ya construye el front; AC1 se verifica en una máquina limpia. |
| Puerto 8000 o 5000 ocupado | El README documenta cómo liberar o reasignar el puerto. |

## 5. Alternativas descartadas

- **HTTPS en GPU alquilada (Vast.ai/Lambda)**: costo y preparación; fuera de alcance desde HU-14.
- **Gradio en `:7860`**: retirado por HU-15.
- **Locust/k6 para latencia**: sobredimensionado para 30 solicitudes secuenciales.

## 6. Estrategia de pruebas

- Unitarias (`tests/test_smoke_deploy.py`, AAA, sin red): el cliente HTTP se simula con
  `httpx.MockTransport`; se verifican el cálculo de p50/p90, el CSV de salida y el
  código de salida ante un fallo.
- Manual en vivo: `make up`, `uv run python scripts/smoke_deploy.py --n 5` (AC4) y
  `--n 30` (AC3), `make down` y `docker ps` vacío (AC5).
