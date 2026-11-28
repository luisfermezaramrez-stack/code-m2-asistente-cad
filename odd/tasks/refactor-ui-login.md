# Refactor de la interfaz: acceso, menú y orden de la solicitud

Especificación de trabajo (ODD) del refactor de interfaz de la entrega M2 Asistente CAD.
Las specs formales viven en `specs/059`, `specs/060` y `specs/061`.

## Specs

- **S1** — «mientras la sesión sea requerida y no esté autenticada, la aplicación renderiza
  únicamente la pantalla de acceso: marca, título, formulario (usuario y clave) y el botón de
  tema. No se renderizan la navegación, el aviso profesional, la vista de trabajo ni sus
  paneles.» (SPEC-059, RF-1)
- **S2** — «el botón de tema usa los iconos de luna y sol como única representación visual de
  la acción: luna cuando el tema activo es claro (la acción lleva a oscuro) y sol cuando el
  tema activo es oscuro (la acción lleva a claro). Conserva un nombre accesible que describa
  la acción, no el icono.» (SPEC-059, RF-2)
- **S3** — «si el servicio no exige sesión (`requerido: false`, modo local), la aplicación abre
  directamente el shell, sin pantalla de acceso intermedia.» (SPEC-059, RF-6)
- **S4** — «la navegación principal contiene exactamente tres entradas: «Nueva solicitud»,
  «Historial» y «Plantillas».» (SPEC-060, RF-1). «Plantillas» (HU-49) es una función de la
  aplicación y se conserva.
- **S5** — «las rutas `/metricas` y `/ajustes` dejan de existir; navegar a ellas resuelve en la
  vista de ruta no encontrada.» (SPEC-060, RF-2)
- **S6** — «el endpoint `GET /v1/metricas` y su módulo `m2_cad.metricas` permanecen intactos
  como contrato de la API (…): la retirada es de interfaz, no de backend.» (SPEC-060, RF-5)
- **S7** — «la card de proceso debe quedar inmediatamente debajo de donde se describe la
  pieza» (pedido del usuario, L1). (SPEC-061, RF-1)
- **S8** — «quiero insertar de manera compacta la card de proceso debajo del boton de generar
  pieza» (pedido del usuario, L4). La card vive dentro del panel «Describe tu pieza», después
  de las acciones, sin borde ni fondo de panel propio y con título de menor jerarquía visual.
  (SPEC-061, RF-1 y RF-2, segunda iteración)
- **S9** — «eliminar este label "Diseño preliminar: requiere revisión profesional / La
  verificación geométrica no certifica resistencia ni cumplimiento normativo."» (pedido del
  usuario, L4). El shell deja de mostrarlo; la marca preliminar sigue en el campo `aviso` de
  la API. (SPEC-062, RF-1 y RF-2)

## Tasks

| ID | Spec | Ruta | Commit |
| --- | --- | --- | --- |
| T1 | S1, S2, S3 | in-line | `feat(hu-58): pantalla de acceso como primera vista y tema sol/luna` |
| T2 | S4, S5, S6 | in-line | `refactor(hu-59): retirar Métricas y Ajustes de la interfaz` |
| T3 | S7, S8 | in-line | `refactor(hu-60): mover la card de proceso bajo la descripción` |
| T4 | S1-S9 | in-line | `test(hu-58-60): cubrir acceso, menú y orden del panel de proceso` |
| T5 | S9 | in-line | `refactor(hu-61): retirar el aviso profesional del shell` |

## Log

- **L1** (pedido original, verbatim): «crea una spec para refactorizar el diseño del front-end
  el login para que la primera pantalla sea el login y solo tenga acceso ca cambiar el tema
  claro a oscuro y biceversa(usar el icono de luna y sol para tema claro y oscuro) y al hacer
  login vea las funciones del app y evitar lo que hacer hoy que muestr el login arriba y el
  resto del app en la primera pantalla / Ademas eliminar las pestañas de metricas y ajustes, /
  la card de proceso dejar debajo de donde se describe la pieza / agrega las spec que sean
  necesarias y agrega las historias de usuario en github project para ejecutarlas»
- **L2**: «primero quiero ver el diseño en local antes de hacer el PR» — el PR y la creación de
  las historias en el GitHub Project quedan en espera del visto bueno sobre la vista local.
- **L3**: decisión del responsable sobre «Métricas»: se borra la vista y sus pruebas; el
  endpoint `/v1/metricas` permanece en la API (S6).
- **L4**: «ademas eliminar este label "Diseño preliminar: requiere revisión profesional / La
  verificación geométrica no certifica resistencia ni cumplimiento normativo." / quiero
  insertar de manera compacta la card de proceso debajo del boton de generar pieza» — segunda
  iteración de diseño tras ver la vista local (S8, S9).
