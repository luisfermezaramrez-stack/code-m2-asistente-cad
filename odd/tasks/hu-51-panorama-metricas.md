# HU-51 · Panorama de métricas sobre MLflow

Issue #111 · SPEC-052 · 1 SP · Ola 3 · Hito M4 · Etiquetas: ML · 1 SP = 1 día.

Rama `feature/hu-51-panorama-metricas`. Specs y criterios:
`specs/052-hu-51-panorama-metricas/spec.md`.

## Specs

S1 — RF-1: «endpoint `GET /metricas` con agregados en una ventana de tiempo: solicitudes,
piezas entregadas, declinaciones por causa (SPEC-027), latencia y costo.»

S2 — RF-2: «los datos se leen de MLflow o del registro existente; no se crea otro almacén.»

S3 — RF-3: «vista en la UI con los agregados y un tablero de costo acumulado. Supuesto:
tablas y cifras simples, sin librería de gráficos nueva.»

S4 — RF-4: «enlace a la UI de MLflow para el detalle por corrida.»

S5 — RNF-1: «las pruebas no usan red, API key ni GPU; MLflow se simula.»

S6 — RNF-2: «si MLflow no está disponible, `/metricas` responde con un estado degradado
explícito, sin error 500.»

S7 — RNF-3: «no se exponen textos de solicitudes ni datos personales en los agregados.»

S8 — AC1: «**Dado** corridas registradas con entregas y declinaciones de varias causas /
**Cuando** se consulta `GET /metricas` / **Entonces** responde los totales, el desglose por
causa, la latencia media y el costo.»

S9 — AC2: «**Dado** el seguimiento desactivado o MLflow caído / **Cuando** se consulta
`GET /metricas` / **Entonces** responde un estado degradado legible y la UI lo muestra sin
romperse.»

S10 — AC3: «**Dado** la vista de métricas abierta / **Cuando** hay datos disponibles /
**Entonces** muestra el costo acumulado y enlaza a MLflow para el detalle.»

S11 — Fuera de alcance: «Reemplazar o replicar la UI de MLflow.», «Alertas de regresión
(SPEC-047).», «Métricas de infraestructura (CPU, memoria).»

S12 — Métricas de éxito: «Las cifras de `/metricas` coinciden con las de MLflow para la misma
ventana.» y «Tiempo de respuesta de `/metricas` aceptable para uso interactivo (< 1 s).»

## Tasks

- [x] T1 — S1, S2, S7 · agregación pura de corridas en una ventana (totales, causas,
      latencia, costo) y lectura de MLflow con error propio · `src/m2_cad/metricas.py`,
      `tests/test_metricas.py`.
- [x] T2 — S1, S6, S8, S9 · `GET /metricas` tipado, autenticado, con ventana `horas` y estado
      degradado explícito · `src/m2_cad/api.py`, contrato regenerado.
- [x] T3 — S3, S4, S10 · vista de métricas con costo acumulado y enlace a MLflow, sin
      librería de gráficos nueva · `frontend/src/views/MetricsView.vue`, router y navegación.
- [x] T4 — S5, S11, S12 · pruebas sin red (MLflow simulado y file store temporal) y
      `make check` en verde.

## Log

L1 — Pedido: «Con qué otra actividad podemos avanzar» y, tras la propuesta, el humano eligió
«HU-51 · Panorama de métricas sobre MLflow (#111)». Fuente de requisitos:
`specs/052-hu-51-panorama-metricas/spec.md` (AC1 agregados, AC2 MLflow ausente, AC3 vista en
la UI). Se advirtió que HU-37 (historial) trabaja en otro worktree sobre la misma SPA: el
cambio en `App.vue`/`router.ts` se mantiene en una línea por archivo para que el conflicto,
si aparece, sea trivial.

L2 — Estado de partida: `origin/main` en `094fe9b` (PR #144 de HU-41 mergeado); la rama se
creó desde ahí en la checkout principal.

L3 — Evidencia de AC1: cuatro corridas reales en un file store temporal (dos entregadas con
latencia y costo, dos declinadas con causa distinta) → `GET /v1/metricas` responde 200 con
`solicitudes: 4`, `entregadas: 2`, `declinadas: 2`, `declinaciones_por_causa` con las dos
causas, la media exacta de latencia y la suma de costo; los contadores se comparan además
contra `search_runs` de MLflow para la misma ventana (`tests/test_metricas.py`).

L4 — Evidencia de AC2: con `Configuracion(activo=False)` o con un `tracking_uri` inexistente,
el endpoint responde **200** con `disponible: false`, `motivo` en español y agregados vacíos;
la vista muestra el aviso con botón de reintento. Nunca 500.

L5 — Evidencia de AC3: `MetricsView.vue` muestra solicitudes, entregadas, declinaciones,
errores, latencia media, costo acumulado (`USD x.xxxx`), la tabla de causas y el enlace
`target="_blank" rel="noopener noreferrer"` a la UI de MLflow; su prueba Vitest afirma el
costo, el enlace y el estado degradado.

L6 — Contrato: `GET /v1/metricas` es aditivo y viaja con `PanoramaMetricas` (13 campos) en
`contracts/openapi-v1.json` y `frontend/src/generated/api.ts` regenerados. Ventana `horas`
validada por el contrato (`ge=1`, `le=720`) → fuera de rango es 422. Sin cambios en `/generar`
ni en el registro.

L7 — Coordinación con HU-37: el cambio en `App.vue` (una entrada de navegación) y en
`router.ts` (una ruta) se mantiene en una línea por archivo para que el conflicto con la rama
de historial, si aparece, sea trivial.

L8 — Revisión nativa aprobada (linaje `review-029117b7ec6ef46e`, tier medium, lentes risk,
readability y reliability) y corrección de sus diez hallazgos informativos en una tanda, con
prueba en rojo por punto:

- R1-1/R1-2: el `motivo` degradado es un mensaje fijo en español; el detalle técnico
  (excepción, URI, rutas) va sólo al log, redactado. RED: el motivo contenía
  `RuntimeError: falló http://host:5000/mlruns … clave=clave-interna`.
- R2-002: `entregadas_por_familia` entra en el agregado y el contrato, así que el docstring y
  el plan dejan de prometer un desglose inexistente. RED: `KeyError: 'entregadas_por_familia'`.
- R2-003: `seguimiento.preparar_entorno` es pública y es la que usa el módulo. RED:
  `AttributeError: module 'm2_cad.seguimiento' has no attribute 'preparar_entorno'`.
- R2-004: `_en_ventana` es el único predicado y sólo lo usa `resumir_corridas`. RED:
  «leer_corridas ya no vuelve a decidir la ventana en memoria».
- R3-silent-page-cap: lectura paginada y filtrada en el servidor; con 1.050 corridas dentro de
  la ventana el panorama cuenta 1.050. RED: `assert 1000 == 1050`.
- R3-no-backend-timeout: plazo `ESPERA_BACKEND_S = 5` con restauración del valor previo. RED:
  `AttributeError: module 'm2_cad.metricas' has no attribute 'ESPERA_BACKEND_S'`.
- R3-error-no-retry: la vista ofrece «Reintentar» también cuando falla la petición.
- R1-3: la vista sólo pinta el enlace a MLflow si es `http(s)`.
- R2-001: el bloque de `/metricas` se movió debajo de `/uso`, para que el comentario de
  autorización y gasto global siga pegado al endpoint que documenta.

El contrato se regeneró (campo aditivo `entregadas_por_familia`) y `make check` quedó en
verde después de la tanda.
