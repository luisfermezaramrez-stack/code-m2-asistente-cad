# Plan de implementación · HU-45 (SPEC-046)

- **Rama**: `feature/hu-45-cola-persistente`, creada desde `origin/main`.
- **Dependencia**: [SPEC-031](../031-hu-30-persistencia-registro/spec.md), ya cerrada.
- **Orden**: spec → plan → tareas → código → pruebas → documentación → PR.
- **Nota de integración**: PR #130 (HU-31) y PR #131 (HU-32) siguen abiertos. Este trabajo no
  depende de `/v1` ni del control de uso; al fusionar se resolverá `api.py`.

## Objetivo

Que las solicitudes SSE sobrevivan a un reinicio y sean ejecutadas por un worker separado,
sin cambiar el contrato de `/generar`, `/generaciones` ni el formato SSE.

## Decisiones de diseño

1. **Cola en archivo, no SQLite nueva.** `src/m2_cad/cola_trabajos.py` guarda un JSON en
   `M2_COLA_PATH` (por defecto `data/cola.json`) usando `_bloqueo` y `_publicar_bytes` de
   `persistencia_registro` (SPEC-031). Así se reutiliza la atomicidad ya probada y no se
   modifica el CSV de registro ni sus consumidores.
2. **Contrato interno compatible.** `TrabajoPersistido` expone `id`, `estado()`, `cancelar()`
   y `eventos()` con la misma forma que `Trabajo`, de modo que `RespuestaSSE`,
   `EstadoTrabajo` y los clientes no cambian. La ruta JSON y `GestorTrabajos` siguen
   intactos; el gestor queda como fallback para trabajos heredados en memoria.
3. **Worker separado.** `python -m m2_cad.worker` (target `make worker`) reclama trabajos,
   ejecuta el procesador y publica eventos. El procesador por defecto es
   `m2_cad.api:procesar_con_progreso`; `--procesador modulo:funcion` permite inyectar el
   simulador en pruebas. La API sólo encola: no ejecuta el pipeline del trabajo SSE.
   Compatibilidad: `M2_COLA_HABILITADA=1` es el valor de despliegue; `tests/conftest.py` lo
   fija a `0` para la batería SSE heredada, que ejecuta en proceso. Las pruebas de HU-45 lo
   reactivan explícitamente y usan el procesador real para verificar el worker separado.
4. **Reanudación.** `reanudar()` devuelve a `pendiente` los trabajos `en_proceso` de un
   worker caído; `reclamar()` marca atómicamente `en_proceso`, guarda `propietario` e
   incrementa `intentos`. Un trabajo terminal nunca se reclama de nuevo.
5. **Registro sin duplicados.** El worker llama a `registrar(identificador=id, ...)`, que
   ya deduplica por `id` (SPEC-031). Además guarda `registrado=true` para que una
   reanudación después de registrar pero antes de publicar el terminal no repita la
   corrida; las métricas se reconstruyen desde la configuración y `medicion` persistidas.
6. **Drenaje ordenado.** `cerrar()` fija `aceptando=false`; `/generar` responde 503 ante
   nuevas solicitudes. El worker termina el trabajo en curso, publica su evento terminal
   y entonces sale. Los eventos se escriben completos y de forma atómica: el lector SSE
   nunca observa un evento a medias.
7. **Consultas y cancelación.** `/generaciones/{id}` y `DELETE /generaciones/{id}` consultan
   primero la cola y caen al gestor en memoria si no existe allí; se conservan 404/200/202.
8. **Retención.** `_limpieza_periodica` no depura `outputs/` mientras la cola tenga
   trabajos activos, además de los trabajos en memoria.
9. **Pruebas.** Sin red, API key ni GPU: procesador simulado, cola temporal y secreto
   efímero `M2_DOWNLOAD_SECRET`. Se prueba reinicio, drenaje SSE, worker en otro PID y
   deduplicación del registro.
10. **OpenAPI.** No se añade ni cambia un campo público, así que `api-types-check` debe
    seguir verde sin regenerar; se verifica de todos modos.

## Criterios de aceptación cubiertos

| AC | Evidencia prevista |
|----|--------------------|
| AC1 | Trabajo `en_proceso` de un worker caído → `reanudar()` + nuevo worker → terminal, con una sola fila en el registro. |
| AC2 | Suscripción SSE activa + `cerrar()` → el último evento es terminal y parsea como JSON completo. |
| AC3 | Encolar desde la API y ejecutar el worker en otro proceso → marker con PID distinto. |

## Riesgos y fuera de alcance

- Un reinicio después de registrar pero antes de publicar el terminal puede repetir el
  procesamiento del modelo; no duplica la fila del registro (RNF-3). Se documenta como
  límite conocido, con el flag `registrado` mitigando la ventana.
- No se escala horizontalmente ni se add prioridades/reintentos del modelo (SPEC-048/026).
- No se tocan HU-31/HU-32 ni se fusionan sus PRs.
