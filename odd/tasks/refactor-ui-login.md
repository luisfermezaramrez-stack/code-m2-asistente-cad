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
- **S10** — «quiero que donde se describen las piezas ocupe el 100% debajo la vista 3D y por
  utlimo la seccion de archivos de la pieza tambien al 100% / En orden quedaria card 1 describe
  la pieza (adentro la card de proceso). 2. card de vista 3D y por ultimo archivos de la
  pieza» (pedido del usuario, L5). Una sola columna al 100 % con ese orden. (SPEC-061, RF-1 a
  RF-4, tercera iteración)
- **S11** — «cambiar el describe la pieza con un 75% y 25% para la card de proceso (compactarla
  al maximo)» (pedido del usuario, L6). Dentro de la card 1: formulario 75 %, proceso 25 %,
  compactado al máximo sin perder estado, etapas ni ayudas. (SPEC-061, RF-3, RF-4 y RF-7,
  cuarta iteración)
- **S12** — «separar la card de proceso de la descripcion de la pieza» (pedido del usuario, L7).
  El proceso deja de estar anidado: es una card propia en la misma fila, 75 % / 25 %.
  (SPEC-061, RF-3 y RF-4, quinta iteración)
- **S13** — «ademas agregar un color gradiente que haga alucion a lo que es el app» (pedido del
  usuario, L7). Token `--gradiente-app` de tonos acero en los tres bloques de tema, aplicado a
  la cabecera del shell y del acceso, sin cambiar colores de texto ni contraste. (SPEC-063,
  RF-1 a RF-5)
- **S14** — «hacer que la card de proceso tenga el mismo alto de la card de describe tu pieza
  (cambia este titulo por otro mas diciente). / dale mas color al modo claro para que no se vea
  tan blanco» (pedido del usuario, L8). Igual alto en la fila (`align-items: stretch`), título
  «Especifica la pieza que necesitas» y paleta clara en tonos acero sin perder AA.
  (SPEC-061, RF-8 y RF-9; SPEC-063, RF-6 y RF-7)

## Tasks

| ID | Spec | Ruta | Commit |
| --- | --- | --- | --- |
| T1 | S1, S2, S3 | in-line | `feat(hu-58): pantalla de acceso como primera vista y tema sol/luna` |
| T2 | S4, S5, S6 | in-line | `refactor(hu-59): retirar Métricas y Ajustes de la interfaz` |
| T3 | S7, S8 | in-line | `refactor(hu-60): mover la card de proceso bajo la descripción` |
| T4 | S1-S9 | in-line | `test(hu-58-60): cubrir acceso, menú y orden del panel de proceso` |
| T5 | S9 | in-line | `refactor(hu-61): retirar el aviso profesional del shell` |
| T6 | S10 | in-line | `refactor(hu-60): una columna al 100 % con descripción, vista 3D y archivos` |
| T7 | S11 | in-line | `refactor(hu-60): proceso al 25 % junto al formulario, compactado al máximo` |
| T8 | S12 | in-line | `refactor(hu-60): card de proceso separada de la descripción` |
| T9 | S13 | in-line | `feat(hu-62): gradiente de identidad en las cabeceras del shell y del acceso` |
| T10 | S14 | in-line | `refactor(hu-60-62): igual alto en la fila, título diciente y paleta clara con color` |

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
- **L5**: «ademas quiero que donde se describen las piezas ocupe el 100% debajo la vista 3D y
  por utlimo la seccion de archivos de la pieza tambien al 100% / En orden quedaria card 1
  describe la pieza (adentro la card de proceso). 2. card de vista 3D y por ultimo archivos de
  la pieza» — tercera iteración: una columna, tres cards al 100 % (S10).
- **L6**: «cambiar el describe la pieza con un 75% y 25% para la card de proceso (compactarla al
  maximo)» — cuarta iteración: 75/25 dentro de la card 1 (S11).
- **L7**: «separar la card de proceso de la descripcion de la pieza / ademas agregar un color
  gradiente que haga alucion a lo que es el app» — quinta iteración: card propia en la fila
  75/25 (S12) y gradiente de identidad en las cabeceras (S13).
- **L8**: «hacer que la card de proceso tenga el mismo alto de la card de describe tu pieza
  (cambia este titulo por otro mas diciente). / dale mas color al modo claro para que no se vea
  tan blanco» — sexta iteración (S14). Además, instrucción explícita de **no hacer commit** de
  estos cambios.
- **L9**: «listo lo primero que debes hacer es crear las HU en proyecs y luego hacer commit el
  diseño quedo bien» — diseño aprobado. HUs creadas en el proyecto 1: **#164 a #169**, hito M5;
  después se commitea el refactor y se abre el PR que las cierra.
- **L10**: «al crear las Hu comenzamos con la implementacion de las misma para luego hacer los
  PR respectivos» — implementación completada en la rama; el PR queda como último paso.

## Slices de entrega

El refactor se entrega en un solo PR (#170) por ser un único cambio de interfaz con archivos
compartidos entre las seis HU. Tamaño medido contra `main`: 29 archivos, +1088 −454.

| Slice | Contenido | Líneas |
| --- | --- | --- |
| S1 | Código y pruebas del frontend (`frontend/`), incluidas las vistas retiradas | +342 −454 |
| S2 | Specs, índice y este documento | +746 |

Si la revisión pide menos carga, S2 se separa a un PR encadenado: las specs no necesitan
revisión de código y el código queda en ~800 líneas, de las cuales casi la mitad son archivos
eliminados completos (MetricsView, SettingsView, Metrics.test).
