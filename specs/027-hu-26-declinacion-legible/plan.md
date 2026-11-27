# SPEC-027 — HU-26 · Plan técnico

Issue: #86 · Rama: `feature/hu-26-declinacion-legible` · Destino PR: `main`.

## Alcance y diseño

El problema no es que falte un mensaje: es que hoy el motivo es **texto libre de dos
orígenes distintos** (la razón cruda del modelo y los mensajes del verificador) y por eso
no sirve ni para el usuario ni como dimensión de métricas. El diseño separa tres cosas
que hoy están mezcladas:

| Responsabilidad | Antes | Después |
|---|---|---|
| ¿Por qué se declinó? | texto libre | `Causa`, catálogo cerrado (S1, S2) |
| ¿Qué lee el usuario? | razón cruda o diagnóstico del verificador | mensaje por causa, en español, con «qué haría falta» (S3) |
| ¿Qué se guarda para diagnóstico y métricas? | el mismo texto | `detalle` técnico aparte + campo/etiqueta `causa` (S4, S5) |

- **Módulo nuevo `src/m2_cad/declinacion.py`**: `Causa` (enum de cadenas), la tabla
  `QUE_HARIA_FALTA` por causa, `mensaje(causa, contexto=None)` y
  `causa_de_informe(informe)`. Es el único lugar con la lista de causas; el pipeline y la
  API lo consumen, no lo duplican.
- **La causa se asigna en el origen, nunca se adivina del texto libre.** El informe de
  `constraint-kit.dsl.check` es estructurado (`severity`, `code`, `path`), y la tabla
  mapea esos códigos:

  | Evidencia estructurada | Causa |
  |---|---|
  | `declined: true` (el modelo respondió `{"unsupported": …}`) | `familia_no_soportada` |
  | `defs` o más de una parte (`pipeline.validar_catalogo`) | `familia_no_soportada` |
  | `unknown-part-type` y ningún otro error | `familia_no_soportada` |
  | `part-build-error` (las medidas no producen geometría construible) | `dimension_incoherente` |
  | salida del modelo sin programa interpretable (`ErrorGeneracion`) | `texto_ambiguo` |
  | cualquier otro error de verificación | `verificacion_fallida` |
  | comparación geométrica contra referencia fuera de tolerancia (SPEC-024) | `fuera_de_tolerancia` |

  `fuera_de_tolerancia` entra al catálogo como exige S1 pero hoy **no tiene productor** en
  el pipeline: el runner del corpus (SPEC-024 AC2) es su consumidor natural. Se documenta
  en lugar de inventar una heurística.
- **`pipeline.py`**: `PiezaDeclinada` gana `causa`; `ErrorVerificacion` y
  `ErrorGeneracion` ganan `causa`, `mensaje` y conservan el detalle técnico. `_declinar`
  pasa a recibir la causa y un contexto legible; la razón cruda del modelo viaja sólo en
  `detalle` (S5). `str(exc)` de `ErrorVerificacion` sigue siendo el texto técnico —lo usan
  las pruebas y el diagnóstico— y la API publica `mensaje`.
- **`api.py`**: el 422 se mantiene (S7) y su `detail` pasa a ser el mensaje legible; el
  detalle técnico no se muestra. La causa se propaga por el `medido` que ya comparten las
  dos rutas (`procesar_con_pipeline` y `procesar_con_progreso`), sin tocar la firma de
  `_clasificar` ni el payload SSE.
- **`registro.py`**: columna `causa`, aditiva y al final de `CAMPOS`, con `"ninguna"`
  cuando no aplica (SPEC-004 AC3: ningún campo vacío). La migración de CSV anteriores se
  generaliza desde `_asegurar_columna_usuario`: añade las columnas que falten con su valor
  por defecto y conserva todas las filas, de modo que un archivo anterior a HU-53 y a
  HU-26 se migra en una sola pasada (S13, coordinación con SPEC-031).
- **`seguimiento.py`**: `Corrida.finalizar` acepta `causa_declinacion` y la escribe como
  etiqueta junto a `motivo_declinacion`, que sigue siendo el texto legible. En las rutas de
  la API la etiqueta siempre existe (`"ninguna"` si la solicitud no se declinó), para que
  sea una dimensión agregable por SPEC-047 y SPEC-052 (S10).
- **Contrato `/v1` sin cambios de forma.** La causa no viaja en el cuerpo: en `main` la
  respuesta de declinación ya es un 422 con `detail` de texto y la cabecera
  `X-Resultado-Tipo`; se conservan ambos. Por eso **no** hay regeneración de tipos del
  frontend: `make api-types-check` y `make api-contract-check` deben seguir en verde sin
  tocar `frontend/src/generated/api.ts` ni `contracts/openapi-v1.json`. Lo único que
  cambia para quien consume es el **texto** de `detail`, que pasa a ser legible.
- **No** se amplía el catálogo de piezas ni el criterio de declinación, no se sugiere una
  solicitud corregida y no se construyen alertas ni panorama (S11).

## Integración con SPEC-024 (AC1)

El corpus dorado (`data/corpus_dorado.json`, HU-23) ya está en `main` con tres casos
`resultado: "declina"`, todos programas `{"unsupported": "<motivo>"}`. AC1 se verifica en
dos niveles, sin tocar el corpus congelado:

1. **Corpus real**: una prueba recorre los casos `declina` del corpus versionado y afirma
   que cada uno recibe una causa del catálogo a través del mismo `verificar_programa` que
   ejecuta `scripts/verify_corpus_dorado.py`.
2. **Cobertura de caminos**: una tabla de casos de declinación recorre cada camino que puede
   declinar (rechazo del modelo, ensamblaje, tipo ajeno, medidas incoherentes, error de
   verificación, salida ambigua) y afirma la causa esperada. Una causa del catálogo sin
   productor haría fallar la tabla de cobertura, no pasar inadvertida.

El artefacto del corpus no gana campos: añadir `causa` al JSON congelado cambiaría el
esquema de HU-23 y su comparación (`observado == esperado`), así que es trabajo de esa
especificación. La dimensión de métricas ya existe en el registro y en la corrida de MLflow
(API) y en la corrida hija de cada caso del banco.

## Pruebas (S6, S9, S12)

`tests/test_declinacion.py` (nuevo, AAA, sin red ni GPU):

- catálogo: las cinco causas obligatorias existen, cada una tiene mensaje y «qué haría
  falta», y no hay causas fuera del catálogo;
- AC1: tabla de casos → causa esperada, incluida la forma del corpus;
- AC2: para cada declinación, el mensaje está en español, contiene la frase de «qué haría
  falta», no contiene identificadores del DSL (`plate`, `bore_d`, `unsupported`, `mate`,
  `program`…), no contiene el texto crudo del verificador ni `detalle`, y `detalle` sí se
  conserva;
- clasificación: `part-build-error` → `dimension_incoherente`, `unknown-part-type` →
  `familia_no_soportada`, error estructural → `verificacion_fallida`.

Extendidas: `tests/test_registro.py` (columna `causa`, migración de un CSV de 8 y de 9
columnas), `tests/test_api_seguimiento.py` (etiqueta `causa_declinacion` en la corrida),
`tests/test_pipeline.py` (el motivo ya no incluye la razón cruda del modelo).
