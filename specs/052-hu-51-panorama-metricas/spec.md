# SPEC-052 · HU-51 — Panorama de métricas sobre MLflow

- **ID**: SPEC-052
- **Historia**: issue por crear · Ola 3 (opcional) · Tamaño S · Épica: MLOps
- **Responsable**: Juan Camilo Pérez
- **Depende de**: [SPEC-025](../025-hu-24-logging-estructurado/spec.md),
  [SPEC-027](../027-hu-26-declinacion-legible/spec.md)
- **Rama**: `feature/hu-51-panorama-metricas`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §6

## Problema y contexto

Esta spec es deliberadamente chica. MLflow ya registra parámetros, métricas, etiquetas y
artefactos por corrida (`src/m2_cad/seguimiento.py:126-260`, clase `Corrida`) y versiones
de modelo (`src/m2_cad/seguimiento.py:286-336`), y tiene UI propia en el puerto 5000
(`make mlflow`, `Makefile:87-88`). El costo por solicitud ya se calcula
(`src/m2_cad/seguimiento.py:71-81`). Falta un resumen accesible desde la API y la UI: hoy
no existe un endpoint `/metricas` (las rutas de `src/m2_cad/api.py` son `/health`,
`/registros/...` y `/generaciones/...`).

El ítem 40 del borrador ("Dashboard de métricas") se reformuló y redujo para no duplicar
MLflow (`docs/backlog-v2.md` §7). El alcance es `/metricas`, las etiquetas de causa de
SPEC-027 y el tablero de costo, no un sistema nuevo.

## Historia de usuario

**Como** responsable del servicio, **quiero** un panorama de métricas de uso, calidad y
costo, **para** seguir la salud del asistente sin entrar a la UI de MLflow.

## Requisitos

### Funcionales

- **RF-1**: endpoint `GET /metricas` con agregados en una ventana de tiempo: solicitudes,
  piezas entregadas, declinaciones por causa (SPEC-027), latencia y costo.
- **RF-2**: los datos se leen de MLflow o del registro existente; no se crea otro almacén.
- **RF-3**: vista en la UI con los agregados y un tablero de costo acumulado.
  Supuesto: tablas y cifras simples, sin librería de gráficos nueva.
- **RF-4**: enlace a la UI de MLflow para el detalle por corrida.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU; MLflow se simula.
- **RNF-2**: si MLflow no está disponible, `/metricas` responde con un estado degradado
  explícito, sin error 500.
- **RNF-3**: no se exponen textos de solicitudes ni datos personales en los agregados.

## Criterios de aceptación

### AC1 — Agregados

- **Dado** corridas registradas con entregas y declinaciones de varias causas
- **Cuando** se consulta `GET /metricas`
- **Entonces** responde los totales, el desglose por causa, la latencia media y el costo.

### AC2 — MLflow ausente

- **Dado** el seguimiento desactivado o MLflow caído
- **Cuando** se consulta `GET /metricas`
- **Entonces** responde un estado degradado legible y la UI lo muestra sin romperse.

### AC3 — Vista en la UI

- **Dado** la vista de métricas abierta
- **Cuando** hay datos disponibles
- **Entonces** muestra el costo acumulado y enlaza a MLflow para el detalle.

## Fuera de alcance

- Reemplazar o replicar la UI de MLflow.
- Alertas de regresión (SPEC-047).
- Métricas de infraestructura (CPU, memoria).

## Métricas de éxito

- Las cifras de `/metricas` coinciden con las de MLflow para la misma ventana.
- Tiempo de respuesta de `/metricas` aceptable para uso interactivo (Supuesto: < 1 s).
