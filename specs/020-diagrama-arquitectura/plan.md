# SPEC-020 — Plan del diagrama de arquitectura

- **ID**: SPEC-020 · **Tipo**: refactor · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## 1. Diseño

Camino principal (resaltado):

```text
Diseñador CAD → SPA Vue → FastAPI POST /generar (SSE) → Gestor de trabajos
  → Pipeline CAD → Verificación + B-rep → outputs/<uuid>/ (STEP · GLB · CSV)
```

Dependencias laterales:

| Desde | Hacia | Relación |
| --- | --- | --- |
| Pipeline CAD | API DeepSeek (`deepseek-v4-pro`) | HTTPS, genera el programa DSL |
| FastAPI | Registro de solicitudes (`data/registro.csv`) | traza ligera sin PII |
| FastAPI | Seguimiento (`seguimiento.py`) | una corrida por solicitud |
| Seguimiento | Servidor MLflow (`:5000`) | HTTP interno de Compose |
| SPA Vue | outputs (vía API) | descarga de archivos |

Límites (regiones):

- Contenedor `m2-cad` (`:8000`): SPA servida, FastAPI, gestor, pipeline, verificación,
  registro y seguimiento.
- Contenedor `mlflow` (`:5000`).
- Servicio externo: API DeepSeek.

Tarjetas: errores → HTTP (422 validación y declinación, 503 modelo no disponible),
verificación determinista y privacidad (Ley 1581).

## 2. Decisiones

| Decisión | Porqué |
| --- | --- |
| Rehacer el JSON en vez de parchear | Cuatro de los diez componentes ya no existen; los que quedan cambiaron de líneas. |
| Fijar `meta.repository.revision` en el commit de la spec | Archify verifica cada cita de código contra esa revisión; ese commit contiene el código descrito. |
| Correr Archify desde un clon en el scratchpad | Evita instalar un skill global solo para regenerar el diagrama; se registra el commit de Archify usado. |
| Incluir el enlace al tablero en esta spec | Es documentación viva del README, del mismo tipo que el diagrama, y la rúbrica lo exige. |

## 3. Comandos

```bash
node <archify>/bin/archify.mjs validate architecture docs/arquitectura.json \
  --quality showcase --repo-root . --json
node <archify>/bin/archify.mjs deliver architecture docs/arquitectura.json \
  docs/arquitectura.html --quality showcase --repo-root . --json
```

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Citas de líneas que no coinciden con el código | `validate` con `--repo-root` las verifica y falla si no coinciden. |
| El HTML generado pesa ~0,8 MB | Es el formato autocontenido de Archify; ya estaba versionado así. |
| `arquitectura.browser-check.json` queda desactualizado | Se regenera si `visual-check` está disponible; si no, se declara pendiente. |

## 5. Alternativas descartadas

- **Editar el HTML a mano**: prohibido por el estándar del proyecto; se pierde la fuente reproducible.
- **Diagrama en Mermaid dentro del README**: no cumple el requisito de Archify de la rúbrica.

## 6. Verificación

- `archify validate` con `--repo-root` (AC2) y `archify deliver` (AC3).
- `grep -ci "gemini\|gradio\|llama\|traduccion"` sobre `docs/arquitectura.json` devuelve 0 (AC1).
- Revisión del README (AC4).
