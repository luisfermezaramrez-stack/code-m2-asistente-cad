# HU-35 · Edición iterativa de la pieza

Issue #95 · SPEC-036 · 5 SP · Ola 1 · Hito M4 · Etiquetas: ML, Backend · 1 SP = 1 día.

Rama `feature/hu-35-edicion-iterativa` (apilada sobre `feature/hu-33-prompts-versionados`;
cuando el PR #141 entre a `main`, se rebasa sobre `main`). Specs y criterios:
`specs/036-hu-35-edicion-iterativa/spec.md`.

## Specs

S1 — RF-1: «un endpoint recibe la pieza previa y una instrucción de cambio en español.»

S2 — RF-2: «el resultado incluye el diff entre el programa DSL previo y el nuevo.»

S3 — RF-3: «el programa nuevo pasa por la misma verificación determinista que una
generación inicial.»

S4 — RF-4: «una edición verificada produce una nueva versión de la pieza y conserva la
anterior.»

S5 — RF-5: «cada solicitud mantiene un historial de versiones consultable.»

S6 — RF-6: «si la edición rompe la verificación, se declina con la causa etiquetada de
SPEC-027 y la versión anterior queda intacta.»

S7 — RNF-1: «las pruebas no usan red, API key ni GPU: el modelo se simula.»

S8 — RNF-2: «`/generar` conserva su contrato actual.»

S9 — RNF-3: «cada versión registra la versión de prompt usada (SPEC-034).»

S10 — Supuesto: «la forma de identificar la pieza previa (id de solicitud o programa
enviado por el cliente) se decide en `plan.md`.»

S11 — AC1: «**Dado** una pieza generada y verificada / **Cuando** se envía la instrucción
"hazla 5 mm más gruesa" / **Entonces** se entrega una pieza nueva verificada, con el diff del
programa DSL, y la versión anterior se conserva.»

S12 — AC2: «**Dado** una pieza generada y verificada / **Cuando** se pide un cambio que hace
fallar la verificación / **Entonces** el servicio declina con la causa etiquetada de SPEC-027
y no reemplaza la versión anterior.»

S13 — AC3: «**Dado** una solicitud con dos ediciones / **Cuando** se consulta su historial /
**Entonces** lista las tres versiones en orden, cada una con su programa y sus artefactos.»

S14 — Fuera de alcance: «Historial de solicitudes en la UI (SPEC-038).» / «Plantillas
parametrizadas (SPEC-049).» / «Edición directa del programa DSL por el usuario.»

S15 — Métricas: «Proporción de ediciones que producen una pieza verificada.» y «0 versiones
anteriores perdidas o sobrescritas.»

## Tasks

- [x] T1 — S9, S10 · prompt de edición como artefacto versionado (`prompts/editor-v1.txt` y
      su entrada en el manifiesto, sin tocar `planner-v1`) y almacén de versiones con diff
      estructurado · `src/m2_cad/versiones.py`, `prompts/`, `tests/test_versiones.py`.
- [x] T2 — S1, S3, S6 · camino de edición en el pipeline: prompt de edición, verificación
      determinista reutilizada y declinación con causa · `src/m2_cad/pipeline.py`,
      `tests/test_edicion.py`.
- [x] T3 — S1, S2, S4, S5, S11, S12, S13 · endpoints `POST /v1/generar/{id}/editar` y
      `GET /v1/generar/{id}/versiones`, con aislamiento por usuario, topes y contrato
      regenerado · `src/m2_cad/api.py`, `contracts/`, `frontend/src/generated/`,
      `tests/test_api_edicion.py`.
- [x] T4 — S7, S8, S14 · no regresión de `/generar`, pruebas sin red y sin GPU, `make check`
      y `make prompts-check` en verde · documentación y `CONSTITUTION.md`.

## Log

L1 — Pedido original: «Nueva tarea: implementar HU-35 (issue #95) Edición iterativa de la
pieza. HU-33 está en el PR #141 (aún sin mergear): no toques esa rama. Fuente de requisitos:
specs/036-hu-35-edicion-iterativa/spec.md (AC1 edición verificada, AC2 edición que rompe la
verificación, AC3 historial de versiones); léela completa junto con CONSTITUTION.md,
AGENTS.md y el contrato de prompts de HU-33 (src/m2_cad/prompts.py y
prompts/manifest.toml), del que depende. Pasos: (1) git fetch origin && git switch -c
feature/hu-35-edicion-iterativa origin/feature/hu-33-prompts-versionados (rama apilada sobre
HU-33; cuando #141 entre a main se rebasa sobre main). (2) Es una HU de 5 SP: crea
odd/tasks/hu-35-edicion-iterativa.md (Specs S# citando los AC literalmente, Tasks con ruta y
commit, Log con este pedido como L1) y plan.md y tasks.md en
specs/036-hu-35-edicion-iterativa/. Planifica commits por unidad de trabajo de unas 400
líneas con pruebas y docs junto al comportamiento. (3) Test-first: RED observado por cada AC
antes de implementar, luego GREEN; pytest AAA sin red ni GPU; afirma cada efecto observable
(respuesta, código HTTP, datos persistidos, artefactos). (4) Reutiliza lo existente: el
pipeline y el verificador deterministas, el registro (si agrega columnas, mismo mecanismo de
migración que usuario, causa y prompt), la cola y el worker, la autenticación y el
aislamiento por usuario de HU-53 (un usuario nunca edita ni ve versiones ajenas), los topes e
idempotencia de HU-32, y el cargador de prompts de HU-33 (si necesitas un prompt nuevo para
editar, es un archivo y una entrada nueva en el manifiesto, nunca editar planner-v1). (5) Si
cambias el contrato /v1 (endpoints nuevos o campos), es un contrato consumido: solo cambios
aditivos, regenera los tipos del frontend (make api-types y api-contract) y dilo
explícitamente. Si tocas la UI, usa el sistema de diseño v2 de HU-34. (6) make check debe
pasar, exportando M2_DOWNLOAD_SECRET con al menos 32 bytes aleatorios; también make
prompts-check. Usa siempre directorios temporales con mktemp y no muevas ni borres archivos
locales gitignored como data/registro.csv. (7) Commits Conventional en español
feat(hu-35): ..., SIN Co-Authored-By ni atribución a IA. NO hagas push ni abras PR. Si
aparece el consentimiento de revisión de Gentle AI, déjalo en pantalla para que lo responda
el usuario. Al terminar responde con: commits (hash + mensaje), resultado de make check,
evidencia por AC, cambios de contrato o de formato persistido, archivos tocados y dudas
abiertas. Si te bloquea una decisión de producto, detente y descríbela en vez de asumir.»

L2 — Estado de partida: `origin/feature/hu-33-prompts-versionados` (mergeado con `main` en
`03a0a15`); la rama se creó desde ahí y no se toca la de HU-33.

L3 — Decisiones fijadas en `plan.md`: la pieza previa se identifica por `solicitud_id` (el
id que `/generar` publica en `X-Registro-ID`, ya ligado a un dueño por HU-53), el servidor
toma la última versión verificada de su propio índice, el prompt de edición es un artefacto
nuevo (`editor-v1`, `planner-v1` intacto) y el registro CSV no cambia de forma: la
trazabilidad de la edición vive en `data/versiones/<solicitud>.json` y en los params
`operacion`, `version_pieza` y `solicitud_origen` de MLflow.

L4 — Evidencia de AC1: `httpx`/TestClient sobre `POST /v1/generar/{id}/editar` con el
pipeline simulado → 200, `version = 2`, `diff` con
`{"ruta": "parts[0].params.thick", "antes": 5, "despues": 10}`, STEP nuevo en su propio
directorio y la versión 1 todavía en el historial con su programa original.

L5 — Evidencia de AC2: `ErrorVerificacion` con causa `dimension_incoherente` → 422 con el
mensaje legible de SPEC-027 (incluye «qué haría falta») y el historial sigue con una sola
versión: la anterior no se reemplaza.

L6 — Evidencia de AC3: dos ediciones encadenadas → `GET /v1/generar/{id}/versiones`
devuelve `[1, 2, 3]` en orden, cada una con `programa`, `artefactos`, `prompt` y
`prompt_hash`.

L7 — Contrato: dos rutas nuevas y aditivas. `make api-types` y `make api-contract`
regeneraron `frontend/src/generated/api.ts` y `contracts/openapi-v1.json`; `/generar`
conserva su cuerpo exacto (prueba de no regresión) y no hay cambios de UI.

L8 — Corte de entrega: cuatro commits por unidad de trabajo (`f2836fb` prompt de edición e
historial, `06546d1` edición en el pipeline, `d847f98` rutas de `/v1` con contrato
regenerado, `d6a12e2` documentación), ~1.390 líneas autoradas sobre la punta de HU-33. Se
entregan como una PR apilada sobre #141; al entrar HU-33 a `main` la rama se rebasa y el
diff de la PR queda sólo con lo de esta HU. Push y PR quedan a decisión del humano.
