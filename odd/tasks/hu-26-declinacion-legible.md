# HU-26 · Motivo de declinación legible y etiquetado por causa

Issue #86 · SPEC-027 · 2 SP · Ola 0 · Hito M4 · Etiquetas: ML, Backend · 1 SP = 1 día.

Rama `feature/hu-26-declinacion-legible`. Specs y criterios: `specs/027-hu-26-declinacion-legible/spec.md`.

## Specs

S1 — RF-1: «un catálogo cerrado de causas de declinación, que incluye al menos
`familia_no_soportada`, `dimension_incoherente`, `verificacion_fallida`,
`fuera_de_tolerancia` y `texto_ambiguo`.»

S2 — RF-2: «cada declinación tiene exactamente una causa del catálogo.»

S3 — RF-3: «el mensaje al usuario está en español, sin términos internos del DSL ni del
verificador, e indica qué haría falta para aceptar la solicitud.»

S4 — RF-4: «la etiqueta de causa se persiste de forma estructurada junto al resultado
(registro y seguimiento), separada del texto del mensaje.»

S5 — RF-5: «el detalle técnico se conserva para diagnóstico, pero no se muestra como
mensaje principal.»

S6 — RNF-1: «las pruebas no usan red, API key ni GPU.»

S7 — RNF-2: «se conservan los códigos HTTP actuales (422 para declinación).»

S8 — AC1: «**Dado** el corpus dorado de
[SPEC-024](../024-hu-23-corpus-dorado-nucleo/spec.md) / **Cuando** se procesan sus casos
esperados como declinación / **Entonces** cada uno tiene una causa del catálogo asignada.»

S9 — AC2: «**Dado** cualquier declinación del corpus / **Cuando** se lee el mensaje que
recibe el usuario / **Entonces** está en español, no contiene identificadores del DSL ni
mensajes crudos del verificador, e indica qué haría falta para aceptarla.»

S10 — AC3: «**Dado** una declinación registrada / **Cuando** se consulta el registro o la
corrida de MLflow / **Entonces** la causa aparece como campo o etiqueta estructurada,
utilizable por las alertas de regresión
([SPEC-047](../047-hu-46-alertas-regresion/spec.md)) y por el panorama de métricas
([SPEC-052](../052-hu-51-panorama-metricas/spec.md)).»

S11 — Fuera de alcance: «Ampliar el catálogo de piezas o cambiar el criterio de
declinación.» / «Sugerir automáticamente una solicitud corregida.» / «Construir las
alertas o el panorama de métricas.»

S12 — Métricas de éxito: «Declinaciones del corpus con causa asignada: 100 %.» y
«Mensajes con términos técnicos del DSL o del verificador: 0.»

S13 — Supuesto: «la lista de causas puede crecer al etiquetar el corpus de SPEC-024; toda
causa nueva entra al catálogo, nunca como texto libre.» y «agregar la columna de causa al
registro se coordina con la persistencia de
[SPEC-031](../031-hu-30-persistencia-registro/spec.md) para no migrar dos veces.»

## Tasks

- [x] T1 — S1, S2, S13 · catálogo cerrado `Causa` y clasificación determinista desde el
      informe estructurado del verificador; sin heurísticas sobre texto libre.
- [x] T2 — S3, S5 · mensajes legibles por causa en `PiezaDeclinada`, `ErrorVerificacion` y
      `ErrorGeneracion`, con el detalle técnico aparte.
- [x] T3 — S4, S10 · columna `causa` en el registro (con migración de CSV anteriores) y
      etiqueta `causa_declinacion` en la corrida de MLflow.
- [x] T4 — S8, S9, S12 · corpus de declinaciones en pruebas (una por causa y por camino) y
      aserción de mensaje sin términos técnicos.
- [ ] T5 — S6, S7, S11 · no regresión de `make check`, 422 intacto, `plan.md`/`tasks.md` y
      estado en el índice de specs.

## Log

L1 — Pedido original: «Tarea: implementar HU-26 (issue #86) 'Motivo de declinación legible
y etiquetado por causa'. Fuente de requisitos: specs/027-hu-26-declinacion-legible/spec.md
(AC1 causa en cada declinación del corpus, AC2 mensaje no técnico, AC3 etiqueta como fuente
de métricas); léela completa junto con CONSTITUTION.md y AGENTS.md antes de tocar código.
Pasos: (1) git fetch origin && git switch -c feature/hu-26-declinacion-legible origin/main
(la rama actual hu-29 ya está mergeada; no la toques). (2) Crea
odd/tasks/hu-26-declinacion-legible.md con Specs S# citando los AC literalmente, Tasks y
Log; redacta plan.md y tasks.md en specs/027-hu-26-declinacion-legible/ como pide el
issue. (3) Test-first: RED observado por cada AC antes de implementar, luego GREEN; pruebas
pytest AAA sin red ni GPU. (4) Reutiliza los helpers existentes del
pipeline/verificador/registro y de seguimiento MLflow para la etiqueta; no dupliques
lógica. Si cambias el contrato /v1 (respuesta de declinación), regenera los tipos del
frontend y dilo explícitamente porque es un contrato consumido. (5) make check debe pasar
(cobertura >= 70 %). (6) Commits Conventional en español tipo feat(hu-26): ..., SIN
Co-Authored-By ni atribución a IA. NO hagas push ni abras PR.»

L2 — Estado de partida: `origin/main` queda en `4f689ed`; la rama se creó desde ahí y la
rama previa `feature/hu-29-runbook-operativo` no se tocó.

L3 — Hallazgo de estado: el corpus dorado de SPEC-024 **no está en `main`**; vive en la rama
`feature/hu-23-corpus-dorado-nucleo` (`data/corpus_dorado.json`, 3 casos `resultado:
"declina"`, todos con programa `{"unsupported": "<motivo>"}`). AC1 se cumple sin depender
de esa rama: el catálogo y la clasificación se prueban sobre cada camino que produce
declinaciones y sobre la forma exacta de los casos del corpus (`unsupported`), de modo que
al integrarse SPEC-024 cada caso ya recibe causa del catálogo. `plan.md` deja el punto de
integración escrito.

L4 — Decisiones de implementación: (a) la causa se asigna en el **origen** de la declinación
(quien levanta la excepción), no se infiere del texto libre del modelo; el informe del
verificador aporta el código estructurado (`part-build-error`, `unknown-part-type`, …), que
se mapea con una tabla en un único módulo; (b) el cuerpo de la respuesta `/v1` no cambia
—la causa viaja al registro y a MLflow, no al contrato HTTP— así que no hay regeneración de
tipos del frontend (verificado con `make api-types-check` y `make api-contract-check`);
(c) la columna `causa` del registro es aditiva y se migra con el mismo mecanismo que la
columna `usuario` de HU-53, para no migrar dos veces cuando llegue SPEC-031.
