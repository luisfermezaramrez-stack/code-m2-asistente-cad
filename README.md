# m2-asistente-cad

Asistente CAD que convierte la descripción **en español** de un componente
metálico auxiliar en un modelo CAD **preliminar verificado** (STEP, GLB y lista
de materiales) en minutos — o que **declina con un motivo** cuando no puede
construirlo.

> ⚠️ **Toda salida es preliminar.** La verificación es solo geométrica; la
> resistencia y el cumplimiento de normas (NSR-10, RETIE) exigen revisión de un
> profesional responsable.

## Qué resuelve

Un diseñador CAD o ingeniero describe la pieza en lenguaje natural, por ejemplo:

> "placa de 120 × 120 mm, 6 mm de espesor, 4 agujeros de 12 mm en un círculo
> de 90 mm"

y obtiene, sin redactar prompts en inglés ni usar la consola:

| Salida | Formato | Uso |
| --- | --- | --- |
| Modelo | STEP (ISO 10303) | Abrir en cualquier CAD |
| Vista 3D | GLB | Visualizar en el navegador |
| Lista de materiales | CSV | Corte / compra |

Si la pieza no se puede construir, el asistente declina con un motivo en
español en vez de inventar geometría.

## Alcance

Catálogo cerrado de 8 familias: `plate`, `sheet_bracket`, `adapter`, `flange`,
`spacer`, `tornillería`, `extrusion` y `pipe`.

Fuera de alcance: cálculo estructural, verificación NSR-10/RETIE, Revit/BIM,
reentrenamiento, entrada por imagen, ensamblajes, autenticación y concurrencia.

## Cómo funciona

1. **Traducción** ES→EN conservando números y unidades.
2. **Generación** condicionada con Gemma 4 12B ConstraintKit (GGUF Q6_K sobre
   llama.cpp).
3. **Verificación** geométrica determinista (constraint-kit / CadQuery /
   build123d / OpenCascade): aprueba o declina cada pieza.
4. **Entrega** por FastAPI + Gradio, con registro trazable (texto, resultado,
   latencia y versión del modelo). Plan B: DeepSeek por API.

## Estructura

    m2-asistente-cad/
    ├── src/m2_cad/          traduccion.py · pipeline.py · api.py · interfaz.py · registro.py
    ├── tests/               test_dataset.py · test_translate.py · test_pipeline.py · test_api.py
    ├── data/test_cases.csv  banco de 40 solicitudes
    ├── docs/                manuales y reporte del banco
    ├── Dockerfile · docker-compose.yml
    ├── pyproject.toml · uv.lock
    └── .pre-commit-config.yaml · .github/workflows/ci.yml

## Requisitos

- **Python 3.11+** (contenedor en 3.12) con `uv`.
- **GPU**: 16 GB de VRAM mín. (recomendado 24 GB); el modelo ocupa ~12 GB.
- **Modelo**: `gemma-4-12b-constraintkit-GGUF` (Q6_K, ~9,8 GB), no versionado.
- **Docker** + NVIDIA Container Toolkit para el despliegue.

> El único entorno probado por el autor es el contenedor Docker.

## Instalación y uso

```bash
uv sync --dev     # 1. dependencias (sin pip install)
make check        # 2. Ruff + pytest
make up           # 3. FastAPI (:8000) y Gradio (:7860) con GPU
```

O con Docker:

```bash
docker compose up --build
```

## Metas (objetivos 1–4)

| Indicador | Meta |
| --- | --- |
| Construcción conforme (±2 % volumen / caja) | ≥ 26/30 (85 %) |
| Declinación correcta | ≥ 8/10 |
| Latencia p90 (solicitud → STEP) | ≤ 60 s |
| Autonomía de usuarios (tareas sin ayuda) | ≥ 7/9 |
| Reproducibilidad | 1 comando, CI en verde |

## Licencias

Código propio: **MIT**. Modelo y motor (Gemma, constraint-kit, CadQuery,
build123d, Z3): **Apache 2.0 / MIT**; OpenCascade **LGPL 2.1**;
python-solvespace **GPL-3.0** (obliga solo al distribuir).

## Referencias

- Modelo: <https://huggingface.co/jajmangold/gemma-4-12b-constraintkit-GGUF>
- Motor geométrico: <https://github.com/jajmangold/constraint-kit>
