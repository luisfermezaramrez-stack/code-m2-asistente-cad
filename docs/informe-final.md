# Informe final de métricas y entrega (HU-13)

> Spec: [`specs/017-hu-13-informe-final/spec.md`](../specs/017-hu-13-informe-final/spec.md) ·
> Historia: [#13](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/13) ·
> Modelo: DeepSeek `deepseek-v4-pro` por API (HU-14). Este informe **consolida**
> valores ya medidos y versionados; no realiza mediciones nuevas (fuera de alcance
> de SPEC-017).

## Resumen

El asistente CAD convierte descripciones en español de componentes metálicos
auxiliares en piezas preliminares verificadas (STEP/GLB/CSV) o declina con motivo.
En la corrida real del 2026-11-14 con `deepseek-v4-pro`, las 40 solicitudes del
banco versionado obtuvieron **30/30 construcciones conformes** y **10/10
declinaciones correctas**, con latencia p90 de **4,497 s** (meta ≤ 60 s) y CI en
verde sobre `develop`. La autonomía de usuarios (HU-11) dio **8/9 tareas sin
ayuda** (meta ≥ 7/9) en una prueba de uso **simulada** con los tres integrantes del
grupo, no con usuarios externos.

## Objetivos (metas 1–4 del README)

| Objetivo | Indicador | Meta | Valor medido | Estado | Evidencia |
| --- | --- | --- | --- | --- | --- |
| 1 | Construcción conforme (±2 % volumen / caja) | ≥ 26/30 | **30/30** | ✅ Cumplido | [`docs/hu07/banco-real-…/auditoria.md`](hu07/banco-real-20261114T042139Z-85855d97/auditoria.md) |
| 2 | Declinación correcta | ≥ 8/10 | **10/10** | ✅ Cumplido | [`docs/hu07/banco-real-…/auditoria.md`](hu07/banco-real-20261114T042139Z-85855d97/auditoria.md) |
| 3 | Latencia p90 (solicitud → STEP) | ≤ 60 s | **4,497 s** (n=40: 30 piezas, 9 declinadas) | ✅ Cumplido | [`specs/010-hu-10-despliegue-local/evidencia/latencia.json`](../specs/010-hu-10-despliegue-local/evidencia/latencia.json) |
| 4 | Autonomía de usuarios (tareas sin ayuda) | ≥ 7/9 | **8/9** (simulado, 3 integrantes del grupo) | ✅ Cumplido (simulado) | [`docs/prueba-usuarios.md`](prueba-usuarios.md) · [`specs/006-prueba-usuarios/spec.md`](../specs/006-prueba-usuarios/spec.md) ([#11](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/11)) |
| — | Reproducibilidad | 1 comando, CI en verde | `make up` / `docker compose up --build`; CI ✅ | ✅ Cumplido | [CI de `develop`](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/workflows/ci.yml) |

**Correspondencia objetivo ↔ indicador (SPEC-017 T01):** la tabla de
[Metas del README](../README.md#metas-objetivos-14) lista los indicadores sin
numerar objetivos; esta correspondencia es el supuesto declarado en
[`SPEC-017 spec.md`](../specs/017-hu-13-informe-final/spec.md). No existe un
documento versionado de la propuesta del M2 en el repositorio, por lo que la
confirmación formal de T01 queda pendiente de validar contra ese documento.

Latencia complementaria de la corrida HU-07 (medida por el cliente HTTP del
evaluador): media **2,765 s**, p90 **2,956 s**, sobre la misma corrida de 40 casos
([`auditoria.md`](hu07/banco-real-20261114T042139Z-85855d97/auditoria.md)). El valor
del objetivo 3 proviene de SPEC-010 (despliegue local, 2026-11-13).

## Trazabilidad de la corrida real (HU-07)

Fuente: [`auditoria.md`](hu07/banco-real-20261114T042139Z-85855d97/auditoria.md) ·
[`reporte.md`](hu07/banco-real-20261114T042139Z-85855d97/20261114T042140Z-1303cab4/reporte.md)

- **Fecha:** 2026-11-14, 04:21:39 – 04:23:35 UTC.
- **Base git:** `4d64ee7f2e7b5ae045ea627d203b46018a6d961a` + cambios archivados con manifiesto SHA-256.
- **Modelo:** `deepseek-v4-pro` (versión configurada y reportada por MLflow; no certifica pesos inmutables del proveedor).
- **Tokens:** 26 280 de entrada / 2 700 de salida.
- **Registros:** 40/40 filas únicas en CSV; 40 corridas MLflow `FINISHED` con el mismo `solicitud_id`; 30 STEP reimportados y verificados por SHA-256, volumen y caja dentro de ±2 %.
- **Hashes:** banco `2a23261f…`, banco normalizado LF `3abc990e…`, manifiesto de código `a5988990…`, ZIP del código `033cbe47…`, prompt `b64b187d…`, orquestación `35427ede…`, imagen API `sha256:219d90d7…` (valores completos en la auditoría).
- Sin reintentos, ajustes ni segunda corrida. Los JSON/CSV/STEP crudos se conservan localmente (SPEC-016 RNF-2: solo el Markdown se versiona).

## Reporte del banco (RF-2)

El reporte referenciado por SPEC-017 RF-2 (`docs/reporte-banco.md`) corresponde a
la corrida real publicada en:

- Índice de la herramienta: [`docs/hu07/README.md`](hu07/README.md)
- Auditoría de aceptación: [`docs/hu07/banco-real-…/auditoria.md`](hu07/banco-real-20261114T042139Z-85855d97/auditoria.md)
- Reporte por caso y familia: [`docs/hu07/banco-real-…/reporte.md`](hu07/banco-real-20261114T042139Z-85855d97/20261114T042140Z-1303cab4/reporte.md)

## Estado del tablero

Actualizado el 2026-11-14 por la HU-21 ([#73](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/73)),
refactor de este informe. Conteo sobre los 22 ítems del
[tablero](https://github.com/users/luisfermezaramrez-stack/projects/1/views/1)
(HU-01 a HU-21, más las tarjetas #38 y #61 de HU-14 y HU-16):

**21/22 en Done.** Brecha:

| Issue | Historia | Causa de la brecha |
| --- | --- | --- |
| [#73](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/73) | HU-21 · Refactor del informe final y la trazabilidad de la HU-13 | Esta actualización; se cierra al fusionar su PR |

La etiqueta `v1.0` y la promoción a `main` (AC4 y AC5 de la HU-13) se gestionan en la
HU-20 ([#72](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/72));
a la fecha de esta actualización la etiqueta **todavía no existe** en el remoto.

Gaps técnicos documentados en `specs/*/tasks.md` (tasks sin marcar con su causa):

- **HU-15 T18:** validar el despliegue con inferencia real desde la SPA (el PR #46 usó modelo simulado; el smoke de despliegue de HU-07 sí usó API real).
- **HU-14 T12:** comparación contra la línea base Gemma con traducción y costo (requiere GPU; `costo_usd` publicado vale 0,0).
- **HU-12 T08/T09/T11:** capturas de los manuales, contrato de endpoints y instalación externa cronometrada (≤30 min) pendientes.
- **HU-02 T13/T15:** protección de `data/` en `main` y script de dataset autocontenido.
- **Gate MLflow p95 (HU-16):** `test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms` mide 56,5 ms con cobertura (umbral 50 ms) en la corrida Docker de auditoría; sin cobertura midió 42,79 ms. No se relajó el umbral; causa de instrumentación no aislada.
- **Revisión humana de los 30 STEP:** la verificación de volumen/caja no descarta todas las diferencias de forma (agujeros, posiciones, radios, topología). **Falta revisión humana de cada STEP contra su solicitud antes de cualquier uso de fabricación**; ninguna salida está certificada para fabricar.
- **T01 (esta spec):** confirmación formal de la correspondencia objetivo ↔ indicador con la propuesta del M2 (no versionada en el repo).

## Reproducibilidad y enlaces

| Recurso | Enlace |
| --- | --- |
| Repositorio | <https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad> |
| Tablero (GitHub Projects) | <https://github.com/users/luisfermezaramrez-stack/projects/1/views/1> |
| CI de `develop` | <https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/workflows/ci.yml> |
| Model Card del modelo servido | [`docs/model-card.md`](model-card.md) |
| Evidencia HU-07 | [`docs/hu07/README.md`](hu07/README.md) |
| Evidencia HU-10 (latencia) | [`specs/010-hu-10-despliegue-local/evidence.md`](../specs/010-hu-10-despliegue-local/evidence.md) |

Comando de despliegue: `docker compose up --build -d` (UI en `http://localhost:8000`,
`/health` y MLflow en `127.0.0.1:5000`). Evaluación del banco: `make bench-report`
(gasta tokens). Etiqueta `v1.0`: se creará sobre `main` tras promover este informe (HU-20,
[#72](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/72)).
