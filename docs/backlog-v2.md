# Backlog v2 — Profesionalización de M2 Asistente CAD

> Estado: **aprobado** y redactado como SPEC-024 … SPEC-056 (HU-23 … HU-55). Este documento
> conserva sólo la priorización, la trazabilidad y las reglas de proceso. **La fuente de
> verdad del alcance, las referencias `ruta:línea` y las dependencias son los `spec.md`**
> (índice en [`specs/README.md`](../specs/README.md)), corregidos según la
> [auditoría](./auditoria-specs-024-056.md).
> Base: estado real del repositorio al cierre de SPEC-023 (HU-22, `v1.0` publicada).

## 1. Qué cambia respecto del borrador de 25

El borrador proponía cinco épicas parejas de cinco. La validación contra el código
encontró tres problemas de fondo:

1. **Cinco ítems ya existen o están a medio hacer**: sistema de tokens (24), layout
   responsive (25), base de accesibilidad (28), dashboard/MLflow (40) y Docker
   multi-etapa (45). Especificarlos "desde cero" produce documentación que contradice
   el código.
2. **Dos dependencias invertidas**: la evaluación continua del banco en CI (41) gasta
   tokens reales y necesita primero caché/replay del LLM (37); las alertas de regresión
   (43) necesitan un baseline histórico que sólo existe después de 41.
3. **Falta lo que más justifica "profesional"**: el núcleo determinista (DSL →
   verificación → STEP) corre sus 113 pruebas **sólo en el contenedor del autor**, no
   en CI. Mientras eso siga así, el resto son features sobre una base no verificada.

Resultado: **33 especificaciones (SPEC-024 … SPEC-056)** en cuatro olas, con el ID
ordenado por ejecución: el ID más bajo es siempre lo próximo a tomar.

## 2. Cómo leer cada spec

- **Ola** = prioridad y orden de ejecución, no importancia académica.
- **Tamaño** = S (≤ 1 PR chico), M (1–2 PRs), L (3+ PRs, o PR encadenada).
- **Depende** = spec que debe estar fusionada antes.
- **Hoy** = evidencia del estado actual: vive en la sección «Problema y contexto» de
  cada `spec.md`.
- **HU** = historia única en el tablero; `HU-23` arranca después de `HU-22`.

## 3. Ola 0 — Baratas y de alto retorno

| Spec | Título | Épica | Tamaño | Depende | Owner |
| --- | --- | --- | --- | --- | --- |
| 024 | Corpus dorado del núcleo determinista en CI | Calidad | M | — | Luis Meza |
| 025 | Logging estructurado y trazas correlacionadas | Backend | S | — | Juan Camilo |
| 026 | Reintentos con backoff y caché de respuestas del LLM | Backend | S | — | Juan Camilo |
| 027 | Motivo de declinación legible y etiquetado por causa | Pipeline | S | — | Luis Meza |
| 028 | Tipos del frontend generados desde OpenAPI | Frontend/API | S | — | Carlos |
| 029 | Escaneo de dependencias y secretos en CI | Entrega | S | — | Carlos |
| 030 | Runbook operativo | Entrega | S | — | Carlos |

## 4. Ola 1 — Fundacionales

| Spec | Título | Épica | Tamaño | Depende | Owner |
| --- | --- | --- | --- | --- | --- |
| 031 | Persistencia transaccional, retención y backup del registro | Backend | M | — | Juan Camilo |
| 032 | API `/v1` versionada con contrato congelado | Backend | M | 028 | Juan Camilo |
| 033 | Control de costo, límites de uso e idempotencia | Backend | M | 026 | Juan Camilo |
| 034 | Prompts versionados como artefactos | Pipeline | M | — | Luis Meza |
| 035 | Sistema de diseño v2: tokens, tipografía y modo oscuro | UX | M | — | Carlos |
| 036 | Edición iterativa de la pieza | Pipeline | L | 034 | Luis Meza |
| 037 | Endurecimiento de artefactos y descargas | Backend | S | — | Juan Camilo |

## 5. Ola 2 — Valor visible

| Spec | Título | Épica | Tamaño | Depende | Owner |
| --- | --- | --- | --- | --- | --- |
| 038 | Historial de solicitudes en la UI | UX | M | 031 | Carlos |
| 039 | App shell y navegación por vistas | UX | M | 035 | Carlos |
| 040 | Visor 3D: vistas ortogonales, medidas y captura | UX | M | — | Carlos |
| 041 | Cierre de brechas WCAG 2.1 AA | UX | M | 035, 039 | Carlos |
| 042 | E2E del frontend con Playwright en CI | Calidad | M | 039 | Carlos |
| 043 | Exportación DXF de planos 2D | Pipeline | L | 024, 037 | Luis Meza |
| 044 | Exportación PDF de planos con cotas | Pipeline | M | 037, 043 | Luis Meza |
| 045 | Evaluación continua del banco con respuestas grabadas | MLOps | M | 026, 034 | Juan Camilo |
| 046 | Cola persistente de trabajos y worker | Backend | L | 031 | Juan Camilo |

## 6. Ola 3 — Opcional según tiempo

| Spec | Título | Épica | Tamaño | Depende | Owner |
| --- | --- | --- | --- | --- | --- |
| 047 | Alertas de regresión de calidad | MLOps | M | 027, 045 | Juan Camilo |
| 048 | Despliegue en la nube | Entrega | L | 033, 037, 046 | Carlos |
| 049 | Materiales, tolerancias y BOM con costos | Pipeline | L | 024 | Luis Meza |
| 050 | Plantillas parametrizadas de piezas | Pipeline | M | 036 | Luis Meza |
| 051 | Cortes y secciones en el visor 3D | UX | L | 040 | Carlos |
| 052 | Panorama de métricas sobre MLflow | MLOps | S | 025, 027 | Juan Camilo |
| 053 | Comparación A/B de prompts y modelos | MLOps | M | 034, 045 | Juan Camilo |
| 054 | Autenticación y usuarios | Backend | L | 037 | Juan Camilo |
| 055 | Sitio de documentación publicado | Entrega | M | 030 | Carlos |
| 056 | Releases automáticos con changelog | Entrega | M | 032 | Carlos |

## 7. Trazabilidad: borrador 24–48 → backlog v2

| Borrador | Backlog v2 | Cambio |
| --- | --- | --- |
| 24 Sistema de diseño | 035 | Reformulada: tokens fuera del frontend, tipografía y modo oscuro |
| 25 Layout responsive | 039 | Reformulada: app shell con navegación, no cosmética responsive |
| 26 Historial en la UI | 038 | Mantenida; datos desde el backend, no caché local |
| 27 Visor 3D | 040 + 051 | Partida: ortogonal/medidas/captura (040) y cortes (051) |
| 28 Accesibilidad AA | 041 | Reformulada: cierre de brechas con axe, no auditoría desde cero |
| 29 Edición iterativa | 036 | Mantenida y priorizada; depende de prompts versionados |
| 30 Catálogo de plantillas | 050 | Mantenida; depende de 036 para reutilizar el programa |
| 31 Material y tolerancias | 049 | Mantenida, con BOM con costos; research-first |
| 32 DXF/PDF | 043 + 044 | Partida en dos specs por costo real |
| 33 Declinación legible | 027 | Priorizada a ola 0, con etiquetado por causa |
| 34 Persistencia BD | 031 | Priorizada; absorbe integridad, retención y backup |
| 35 Autenticación | 054 | Bajada a ola 3; el mínimo de seguridad va en 037 |
| 36 Rate limit/costo | 033 | Priorizada; el cálculo de costo ya existe, falta el tope |
| 37 Reintentos y caché | 026 | Priorizada a ola 0; habilita 045 |
| 38 `/v1` y OpenAPI | 032 | Reformulada: versionado y contrato, no "documentar" |
| 39 Logging | 025 | Mantenida, ola 0 |
| 40 Dashboard de métricas | 052 | Reformulada y reducida: no duplicar MLflow |
| 41 Banco en CI | 045 | Repriorizada; depende de 026 y 034 |
| 42 Comparación en MLflow | 053 | Reformulada: hoy no existe artefacto de prompt (034) |
| 43 Alertas de regresión | 047 | Repriorizada tras 045 y 027 |
| 44 Playwright | 042 | Mantenida |
| 45 Docker multi-etapa y nube | 048 | Reformulada: multi-etapa ya existe; sólo despliegue |
| 46 Releases automáticos | 056 | Bajada a ola 3 |
| 47 Escaneo de deps/secretos | 029 | Priorizada a ola 0 |
| 48 MkDocs | 055 | Bajada; el runbook (030) cubre la necesidad operativa |
| — | 024 | **Nueva**: corpus dorado del núcleo determinista en CI |
| — | 028 | **Nueva**: tipos del frontend desde OpenAPI |
| — | 030 | **Nueva**: runbook operativo |
| — | 034 | **Nueva**: prompts versionados como artefactos |
| — | 046 | **Nueva**: cola persistente y worker |
| — | 047 | **Nueva**: alertas de regresión |

## 8. Reglas de proceso

1. **Dos niveles de documento.** `spec.md` completo (problema, requisitos, AC
   Given-When-Then) al crear la spec; `plan.md` y `tasks.md` recién cuando la HU se
   toma. Evita 75 documentos a medio llenar.
2. **Reparto por ola, no por épica.** Un reparto 9/8/8 por épica deja 024 y 036 —las dos
   de mayor impacto— al final del calendario. Con olas, cada desarrollador toma una
   spec terminable por semana.
3. **Cada spec cierra con su evidencia**: PR fusionada, fila en `specs/README.md` y
   registro en el tablero, igual que 001–023.
4. **Las specs que reformulan algo existente citan el código actual** en su encabezado
   (ruta:línea), para que la retroactividad sea explícita y nadie "descubra" que ya
   estaba hecho.
5. **Nada se crea en GitHub hasta aprobar este documento**: las 33 HUs se abren e
   incorporan al tablero `m2-asistente-cad` en el mismo momento en que cada spec se
   redacta, no antes.

## 9. Riesgo declarado del backlog

- **Mayor incógnita técnica**: 049 (materiales y tolerancias de fabricación). El DSL no
  admite tolerancias por cota y el BOM agrupa por tipo de pieza, no por material; exige
  un spike antes de comprometer la HU.
- **Segunda incógnita**: 043 y 044 (DXF/PDF). El kit ya exporta secciones DXF y
  proyecciones ortogonales; lo abierto son las cotas por arista, la capa de aristas
  ocultas y, en 044, una dependencia nueva para generar PDF.
- **Riesgo de calendario**: la ola 3 completa duplica el trabajo de la ola 0–2. Si hay
  que elegir, 047/052/055/056 aportan más por hora invertida que 049/051/054.
