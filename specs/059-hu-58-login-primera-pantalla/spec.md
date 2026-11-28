# SPEC-059 · HU-58 — El login como primera pantalla y el tema sol/luna (refactor)

- **ID**: SPEC-059
- **Historia**: #164 (HU-58) · 2 SP · Etiquetas: frontend, refactor, UX
- **Responsable**: Luis Meza
- **Rama**: `refactor/hu-58-60-interfaz-login` (HU-58, HU-59 y HU-60 en un solo PR)
- **Estado**: Spec-first · en revisión (PR #170)
- **Supera**: el requisito de shell de [SPEC-039](../039-hu-38-app-shell/spec.md) sobre el
  formulario de acceso dentro de la cabecera y el de [SPEC-054](../054-hu-53-autenticacion/spec.md)
  sobre el acceso conviviendo con la vista.
- **Preserva**: la navegación por teclado nativa del shell (SPEC-040/042) y el `tabindex="-1"`
  del destino del skip link, que se mantienen sin cambios.

## Problema y contexto

Hoy `frontend/src/App.vue:79-90` pinta el panel de sesión dentro del mismo flujo que la
cabecera, el aviso profesional y la navegación (`App.vue:61-96`): quien abre la aplicación ve
el formulario de acceso arriba y las funciones de la app abajo. El resultado es una pantalla
que no se lee como una puerta de entrada: el visitante que todavía no se autenticó ve el
formulario de generación, la navegación y el aviso profesional, y puede creer que ya está
dentro del servicio.

Además, el cambio de tema se ofrece como un botón de texto (`App.vue:69`:
`{{ themeLabel }}`) que ocupa espacio y compite con el título, cuando es la única acción
que la pantalla de acceso debe ofrecer además del formulario.

El estado de sesión ya existe y es correcto (`frontend/src/auth.ts`): `estadoSesion()`
consulta `/v1/auth/me`, la cookie HttpOnly la maneja el navegador y, si la lectura falla, se
asume sesión requerida. Lo que falta es la **presentación**: una pantalla de acceso dedicada,
y el shell sólo después de autenticarse.

## Historia de usuario

**Como** visitante del asistente CAD, **quiero** que la primera pantalla sea sólo el inicio de
sesión, con la opción de cambiar entre tema claro y oscuro, **para** entrar al servicio sin
confundir el acceso con las funciones de la aplicación.

## Requisitos

### Funcionales

- **RF-1**: mientras la sesión sea requerida y no esté autenticada, la aplicación renderiza
  únicamente la pantalla de acceso: marca, título, formulario (usuario y clave) y el botón de
  tema. No se renderizan la navegación, el aviso profesional, la vista de trabajo ni sus
  paneles.
- **RF-2**: el botón de tema usa los iconos de luna y sol como única representación visual de
  la acción: luna cuando el tema activo es claro (la acción lleva a oscuro) y sol cuando el
  tema activo es oscuro (la acción lleva a claro). Conserva un nombre accesible que describa
  la acción, no el icono.
- **RF-3**: el botón de tema es un único componente reutilizable
  (`frontend/src/components/BotonTema.vue`), disponible en la pantalla de acceso y en la
  cabecera del shell, con el mismo comportamiento y la misma preferencia persistida
  (`m2-cad-theme`), y sigue respetando `prefers-color-scheme` cuando no hay preferencia.
- **RF-4**: al iniciar sesión con credenciales válidas, la pantalla de acceso se desmonta y el
  shell se monta en la misma ruta, con la vista que el usuario pidió y su nombre visible.
- **RF-5**: un fallo de credenciales, de red o de cierre de sesión se informa dentro de la
  pantalla de acceso, sin mostrar contenido de la app ni detalles internos.
- **RF-6**: si el servicio no exige sesión (`requerido: false`, modo local), la aplicación
  abre directamente el shell, sin pantalla de acceso intermedia.
- **RF-7**: un fallo al leer `/v1/auth/me` mantiene el comportamiento actual: se pide sesión;
  nunca se asume el modo local.

### No funcionales

- **RNF-1**: la pantalla de acceso y su botón de tema cumplen WCAG 2.1 AA: foco visible,
  objetivo táctil de 44 px (`--control-min`), nombre accesible en el botón de icono y orden de
  tabulación formulario → botón de tema.
- **RNF-2**: el icono va como SVG en línea; no se agregan dependencias ni archivos binarios.
- **RNF-3**: la preferencia de tema no se guarda en el servidor ni viaja en la petición de
  login.

## Criterios de aceptación

### AC1 — Primera pantalla: sólo el acceso

- **Dado** un servicio con sesión requerida y un visitante sin autenticar
- **Cuando** abre cualquier ruta de la aplicación
- **Entonces** ve únicamente la pantalla de acceso (marca, formulario y botón de tema) y no
  existe en el DOM la navegación, el aviso profesional ni el panel «Especifica la pieza que necesitas».

### AC2 — Tema con iconos de sol y luna

- **Dado** la pantalla de acceso con el tema claro activo
- **Cuando** pulsa el botón de tema
- **Entonces** el documento pasa a `data-theme="dark"`, el botón muestra el sol y su nombre
  accesible describe la acción de volver al tema claro.

### AC3 — Entrada al shell tras autenticarse

- **Dado** un visitante en la pantalla de acceso
- **Cuando** envía credenciales válidas
- **Entonces** la pantalla de acceso desaparece, el shell se muestra con su nombre y la vista
  pedida, y el botón de tema sigue disponible en la cabecera.

### AC4 — Credenciales inválidas

- **Dado** un visitante en la pantalla de acceso
- **Cuando** envía una clave incorrecta
- **Entonces** ve «Usuario o clave incorrectos.» dentro de la pantalla de acceso y ningún
  contenido de la aplicación.

### AC5 — Modo local sin autenticación

- **Dado** un servicio que responde `requerido: false` en `/v1/auth/me`
- **Cuando** se abre la aplicación
- **Entonces** el shell se muestra de inmediato y no aparece la pantalla de acceso.

## Fuera de alcance

- Cambiar el contrato de `/v1/auth/login`, `/v1/auth/me` o `/v1/auth/logout` (SPEC-054).
- Agregar registro, recuperación de clave, roles o permisos.
- Cambiar los tokens de color o las tipografías (SPEC-035).

## Métricas de éxito

- Ninguna ruta de la SPA renderiza contenido de la aplicación antes de autenticarse.
- Un único camino de tema: una preferencia, dos puntos de acceso (acceso y cabecera).
