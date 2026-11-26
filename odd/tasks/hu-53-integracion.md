# HU-53 · Integración con main y correcciones de revisión (PR #133)

Objetivo: dejar el PR #133 aprobable, integrado con HU-31/32/45 y con los hallazgos de revisión corregidos.
Rama: `feature/hu-53-autenticacion` · Entrega: merge de `main` + commits de corrección en la rama del PR · Pruebas: `make check` (pytest, Vitest).

## Specs

- S1. "corrige este PR para que todo este en orden y poder aprobarlo, ademas resuelve los conflictos": resolver los 10 conflictos con `main` (`2621414`).
- S2. Bloqueante 1: los trabajos de la cola HU-45 guardan su dueño; consultar, cancelar y descargar responden 404 a otro usuario.
- S3. Bloqueante 2: el worker registra el usuario dueño en el CSV y en MLflow.
- S4. Bloqueante 3: con autenticación activa, la idempotencia y los topes de HU-32 se asocian al usuario, no a la IP o `X-Session-ID`.
- S5. Bloqueante 4: `/auth/*` se publica bajo `/v1` y el contrato congelado se regenera.
- S6. Bloqueante 5: un 422 de un usuario autenticado se registra con su usuario.
- S7. Endurecimiento: límite de intentos fallidos en el login (429), sesión invalidada si el usuario se quita o cambia su clave, tiempo de verificación similar para usuarios inexistentes, configuración inválida detectada al arrancar.
- S8. Menores: `auth.ts` no asume modo local ante un error de `/v1/auth/me`; la migración del CSV no se repite en cada `registrar()`.
- S9. Bug de `main`: `descargar_archivo` encuentra los trabajos de la cola.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
| --- | --- | --- | --- | --- |
| T1 | S1 | inline | hecho | d604675 |
| T2 | S2, S3, S9 | inline | hecho | d604675 |
| T3 | S4, S5, S6 | inline | hecho | d604675 |
| T4 | S7 | inline | hecho | d604675 |
| T5 | S8 | inline | hecho | d604675 |
| T6 | S1–S9 | verificador independiente (riesgo: item 2, seguridad) | hecho; correcciones H1–H3, H5, H6 | c36aec1 |

## Log

- L1 (2026-11-25): "corrige este PR para que todo este en orden y poder aprobarlo, ademas resuelve los conflictos"
- L2: hallazgos de la revisión de PR #133 validados por el agente de `w6:p1`; RDD apagado en este clon (`clone_local: off`).
- L3: conflictos resueltos (10 archivos). Correcciones S2–S9 con pruebas nuevas en `tests/test_hu53_autenticacion.py`; cada una validada por mutación (9/9 RED). Decisiones: con autenticación la clave de idempotencia se acota al usuario (evita 409 cruzado) y `/v1/uso` exige sesión. `make check`: 475 pytest (93,31 %), 58 Vitest; smoke HG-15 correcto. Pendiente: `.env.example` sin las variables nuevas (lectura bloqueada por una regla de permisos).
- L4: verificador independiente sobre d604675: sin bypass del aislamiento; S7 parcial. Una tanda de corrección: H1 (límite concurrente), H2 (acierto de otra cuenta reiniciaba), H3 (anónimo escribía en el registro con JSON mal formado), H5 (404 distinguible), H6 (hash con 0 iteraciones). Mutación 6/6 RED tras agregar `test_limite_por_cliente_sobrevive_a_un_acierto`. Documentados sin cambio: H4 (anterior), H7 (diseño), H8 (proxy). `make check`: 481 pytest (93,34 %), 58 Vitest.
- L5 (2026-11-25): "ya habilite el RDD haz la verificacion"
- L6: RDD `review-9e37b007e6c5e6ef` (risk, resilience, readability, reliability) aprobó c36aec1 sin bloqueantes; acuse registrado. 13 hallazgos informativos atendidos en un commit aparte (límite de login acotado, NO_ENCONTRADA único, Compose en modo local, logout fallido visible, aserción Vitest vacua, cancelación propia en cola, docs). `make check`: 483 pytest (93,34 %), 60 Vitest.
