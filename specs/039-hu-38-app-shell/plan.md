# Plan de implementación · HU-38 (SPEC-039)

- **Rama**: `feature/hu-38-app-shell`, creada desde `origin/main` en `a2a9dd7`.
- **Issue**: [#98](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/98).
- **Orden**: spec → plan → tareas → código → pruebas → documentación → PR.
- **Estado al tomar la HU**: AC1, AC2 y AC5 ya implementados en esta rama; se conservan y se completan AC3 y AC4.
- **Auditoría del estándar**: no destructiva, 0 FALTA y 21 DIFIERE; las diferencias son personalizaciones ya declaradas en `CONSTITUTION.md` (Python 3.12, `hatchling`, entre otras).

## Objetivo

Dar al shell tres vistas con URL propia y estado recuperable, estados nuevos distinguibles y navegación operable sin mouse, sin romper el contrato JSON de la API ni el flujo de generación.

## Decisiones de diseño

1. `frontend/src/router.ts` concentra las rutas y expone `createAppRouter(history)`; la app usa `createWebHistory()` y las pruebas `createMemoryHistory()`. `/` redirige a `/nueva-solicitud`.
2. `App.vue` queda como shell: cabecera, aviso profesional, skip link, navegación, panel de sesión y `RouterView`. La generación se extrae a `NewRequestView.vue` y conserva `useGeneration.ts` sin cambios de contrato.
3. `frontend/src/useGeneration.ts` guarda descripción y tiempo de espera en `localStorage` (`m2-cad-draft`); el tema ya se guarda en `m2-cad-theme`. No se introduce persistencia en el servidor.
4. `src/m2_cad/web.py` registra GET/HEAD para `/nueva-solicitud`, `/historial` y `/ajustes` que entregan `index.html`. El resto de rutas —API y `/assets`— siguen respondiendo 404 JSON.
5. `VistaEstado.vue` presenta `vacio`, `cargando` y `error` con clase, color y texto distintos; `NotFoundView.vue` cubre la ruta comodín del router. Los estados de historial y ajustes se seleccionan por `?estado=` sin simular progreso de una solicitud.
6. La navegación usa enlaces reales de `RouterLink`; `App.vue` atiende `Tab`, `Shift+Tab` y `Enter` dentro de `nav` para que foco y activación sean verificables, apoyándose en `:focus-visible` global ya existente.
7. No se añaden tokens ni modo oscuro (SPEC-035), no se implementa contenido del historial (SPEC-038) y no se ejecuta auditoría axe (SPEC-041).

## Criterios de aceptación cubiertos

| AC | Evidencia prevista |
|----|--------------------|
| AC1 | Pruebas de ruta inicial, `href` de los tres enlaces y cambio de vista. |
| AC2 | Pruebas que remount la app en otra historia con la URL copiada; borrador, timeout y tema recuperados. |
| AC3 | Pruebas parametrizadas sobre `vacio`, `cargando` y `error` en historial y ajustes, más ruta desconocida. |
| AC4 | Pruebas de foco con `Tab`/`Shift+Tab`, activación con `Enter` y skip link enfocable. |
| AC5 | Solicitudes HTTP con build real a las tres vistas y a rutas API/assets inexistentes. |

## Riesgos y fuera de alcance

- El build de producción genera un chunk grande para `GlbViewer`; aviso conocido de Vite, sin cambio de código en esta HU.
- Las pruebas backend con build presente requieren `M2_DOWNLOAD_SECRET` con al menos 32 bytes; es efímero de ejecución, nunca versionado.
- El alcance de `?estado=` es presentacional: cuando SPEC-038 conecte el backend, sustituirá la selección manual por el estado real del listado.
