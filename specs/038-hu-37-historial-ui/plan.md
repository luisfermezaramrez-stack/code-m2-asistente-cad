# Plan de implementación · HU-37 (SPEC-038)

- **Rama**: `feature/hu-37-historial-ui`, creada desde `origin/main` en `3363859` (incluye #142 de HU-38 y #143 de HU-35).
- **Issue**: [#97](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/97).
- **Orden**: spec → plan → tareas → pruebas ROJO → código → VERDE → documentación → PR.
- **Punto de partida**: `/historial` era una vista de relleno de HU-38 cuyos estados `vacio`/`cargando`/`error` se elegían con `?estado=`; el backend sólo permitía consultar una solicitud conociendo su id.
- **Reutilización verificada**: HU-31 publicó `/v1` y el contrato congelado sin endpoint de colección; HU-35 añadió `GET /v1/generar/{id}/versiones`, que es historial de versiones de una pieza, no de solicitudes. No había nada que duplicar.

## Objetivo

Que el historial muestre las solicitudes reales del registro persistente, se pueda filtrar y reabrir, y que la reapertura permita descargar el STEP aunque el servidor se haya reiniciado — sin copia autoritativa en el cliente ni cambios en el flujo SSE.

## Decisiones de diseño

1. **Endpoint de listado (RF-5, AC3)**: `GET /v1/registros` con `RespuestaRegistros` y `RegistroResumen`. Campos mínimos: `id`, `hora`, `texto`, `estado` y `motivo`; nunca `usuario`, `prompt`, `prompt_hash`, `traduccion`, `resultado` ni rutas. Filtros `resultado` y `texto` se resuelven en el servidor, orden descendente por `hora` con desempate por `id`, y tope de 200 filas (`LIMITE_HISTORIAL`).
2. **Protección (S6)**: la misma del resto de `/v1`. `usuario_actual` exige sesión y el listado devuelve sólo las filas cuyo `usuario` coincide con el de la sesión (HU-53). No se usa `garantizar_propietario` para filtrar: aquí se compara por igualdad, no se responde 404 por fila.
3. **Lector reutilizable**: `registro.listar(ruta)` y `registro.leer(identificador, ruta)` son el único lector del CSV; `api._leer_registro` los reutiliza conservando su contrato anterior (404 puntual, 422 con id mal formado). Un archivo inexistente es historial vacío; una cabecera ajena sigue siendo un error, porque el backend es la fuente de verdad (RNF-1).
4. **Estado derivado en el backend**: el registro no persiste el estado terminal y cambiar el esquema de SPEC-031 está fuera de alcance. `_estado_registro` aplica una precedencia documentada: `resultado` con `step` → `construida`; `causa` del catálogo de SPEC-027 → `declinada`; `error` distinto de `ninguno` → `error`; sin señal → `desconocida`. El motivo de un fallo es siempre un texto público, nunca la excepción ni una ruta.
5. **Token de descarga para solicitudes antiguas (RF-4, AC4)**: `emitir_token` sólo se emitía al crear o editar una solicitud, así que el STEP de una solicitud pasada era indescargable tras reiniciar. `GET /v1/registros/{identificador}` devuelve ahora `X-Download-Token` **después** de comprobar sesión y propiedad, reutilizando el token HMAC y su TTL existentes; `exigir_token` no se relaja. Si las descargas están deshabilitadas por configuración (sin `M2_DOWNLOAD_SECRET`), la consulta sigue funcionando y el STEP sigue exigiendo token.
6. **Una sola fuente del estado**: la consulta puntual devuelve además `estado` y `motivo`, porque su cuerpo es un mapa libre de texto y añadir claves no cambia el esquema congelado. Así la vista de detalle no reimplementa en TypeScript la precedencia del punto 4.
7. **UI (RF-1, RF-2, RF-3)**: `HistoryView` pide el listado al backend al montar, deriva `cargando`/`error`/`vacio` de esa carga real con `VistaEstado` y deja de leer `?estado=`. Los filtros (resultado y texto) vuelven a consultar al servidor. La reapertura vive en la ruta `/historial/:identificador` (`historial-solicitud` → `HistoryDetailView.vue`), muestra estado y motivo, descarga el STEP con `downloadArtifact` y el token obtenido, y ofrece `GlbViewer` sólo si un `HEAD` con token confirma que el trabajo sigue vivo. No se toca `useGeneration`, `App.vue` ni el flujo SSE.
8. **Nada de caché autoritativa (RNF-1)**: el historial no se guarda en `localStorage`; recargar o abrir desde otro equipo vuelve a pedir el listado.

## Criterios de aceptación cubiertos

| AC | Evidencia prevista |
|----|--------------------|
| AC1 — Persistencia ante recarga | Dos lecturas del mismo registro devuelven las mismas solicitudes (pytest) y remontar la app muestra la misma lista (Vitest). |
| AC2 — Otro equipo | Misma pareja de pruebas: el cliente no guarda nada y el backend prevalece. |
| AC3 — Listado desde un endpoint | `GET /v1/registros` devuelve todas las filas sin que el cliente conozca ningún id; Vitest comprueba que la vista pide ese endpoint. |
| AC4 — Reabrir y descargar | pytest: con el gestor de trabajos vacío (reinicio simulado), el token de `GET /v1/registros/{id}` habilita `/step`; Vitest: reabrir navega, muestra estado y motivo y descarga el STEP con token. |

## Riesgos y fuera de alcance

- Re-descargar GLB y CSV de solicitudes cuyo trabajo ya no vive sigue fuera de alcance: para eso habría que servirlos desde el registro.
- El listado no pagina: devuelve las 200 solicitudes más recientes. Si el registro crece, la paginación será otra historia.
- `GET /v1/registros/{identificador}` sigue devolviendo la fila completa del CSV (incluye `prompt` y `prompt_hash`): recortarla sería un cambio incompatible del contrato v1 y exigiría `/v2`; el listado nuevo, que es el que estrena superficie, no expone esos campos.
- Las filas canceladas se clasifican como `error` con su motivo, porque el registro no persiste el estado terminal y el esquema de SPEC-031 queda fuera de alcance.
- El estado se deriva de columnas que ya existían; si el pipeline cambia el texto de `error`, la clasificación sigue dependiendo de `causa` y de la presencia de `step`, no de ese texto.
