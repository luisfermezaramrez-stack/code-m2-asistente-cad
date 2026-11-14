# HU-15 · Propuesta visual pendiente de aprobación

Abre `design/index.html` directamente en un navegador. No necesita instalación,
servidor ni conexión a Internet. Las hojas CSS deben permanecer junto al HTML.
La maqueta permite escribir y abrir/cerrar muestras; los botones de generación,
cancelación y las descargas son representaciones sin acción.

## Referencia y alcance

Se revisó el cuerpo completo y los comentarios del issue #39: no contiene una
referencia gráfica ni un estilo prescrito. Se propone una interfaz técnica sobria:
superficies claras, azul acero, tipografía del sistema, etiquetas monoespaciadas,
bordes definidos y mensajes explícitos. No se añaden dependencias ni código a la
aplicación. Esta propuesta **no equivale a aprobación** de AC4.

`tokens.css` es la fuente única de colores, tipografía, espaciado y estados.
`reference.css` contiene la composición; `index.html`, la referencia estática.

## Distribuciones de referencia

Usar las herramientas de dispositivo del navegador, con zoom al 100 % y ancho
del viewport en píxeles CSS. Altura sugerida: 1000 px; el scroll vertical es previsto.

| Elemento | 1280 px | 768 px |
| --- | --- | --- |
| Contenedor | Máximo 1216 px, centrado; padding 32 px | Ancho disponible; padding 24 px |
| Área útil interior | 1152 px | 720 px |
| Solicitud | Columna izquierda de 384 px | Primera sección, ancho completo |
| Separación | 24 px | 24 px verticales |
| Proceso, vista 3D, archivos | Columna derecha de 744 px | Debajo de solicitud, en ese orden |
| Muestras de estados | Ancho completo, debajo del espacio de trabajo | Ancho completo, debajo de archivos |
| Archivos disponibles | Tres celdas de ancho flexible | Tres celdas de ancho flexible |

El cambio a una columna ocurre a 900 px. Textos y cabeceras se ajustan; no hay
anchos mínimos que exijan scroll horizontal. El orden del DOM y del teclado
coincide con el orden de lectura en ambas distribuciones. A 480 px los archivos
también pasan a una columna.
Las medidas de la tabla son nominales: con una barra vertical de 15 px, Chrome
deja 705 px interiores a 768 px. La distribución sigue siendo de una columna.

## Estados y contrato visual

- Vacío: ninguna etapa completada ni archivos; descripción editable.
- Cargando: `validando` → `generando`, exclusivamente tras eventos SSE reales.
  Sin eventos: «Progreso no disponible», sin barras, porcentajes ni estimaciones.
- Terminales: `verificado` | `declinado` | `error`. Las muestras aparecen juntas
  solo para revisión y no representan eventos recibidos.
- Cancelar: acción disponible durante la solicitud. Abortar la conexión solo
  detiene la espera local; no demuestra cancelación del procesamiento remoto.
  AC3 exige una solicitud cancelable: definir y probar el contrato backend antes
  de considerar cumplido este criterio. Ver `validation.md`.
- Verificado: vista GLB y descargas STEP/GLB/CSV independientes. Sin GLB, STEP
  permanece disponible. Sin STEP, aviso explícito aunque exista GLB.
- Declinación/error: motivo legible, sin descargas ni modelo de la solicitud previa;
  conservar descripción para corrección o reintento. Timeout configurable.
- Aviso permanente: «Diseño preliminar: requiere revisión profesional».

## Accesibilidad y revisión

Los pares de texto/fondo se eligen para AA (mínimo 4.5:1), incluidos mensajes,
texto secundario y texto de botones. Bordes y foco requieren 3:1 contra las
superficies adyacentes. Estados llevan nombre y explicación, no solo color.
No hay animaciones ni recursos externos. La vista ilustrativa tiene alternativa
textual; no exige arrastre para comprender el resultado.

Revisar con Tab/Mayús+Tab: salto al contenido → descripción → resúmenes de estados;
Enter/Espacio abre o cierra cada muestra. El foco violeta tiene contorno de 3 px.
Los botones nativos deshabilitados no forman parte del tabulado de esta maqueta.
En la aplicación se incorporarán acciones y enlaces habilitados al mismo orden,
anuncios `aria-live="polite"` para eventos reales, errores asociados al campo y
controles de visor utilizables por teclado. No se usan regiones vivas aquí porque
las muestras son estáticas y no deben anunciarse como actividad real.

Verificación estática realizada: estructura HTML, referencias de etiquetas/IDs,
recursos locales, controles inertes y tokens resueltos. Se calcularon 15 pares
de texto/fondo (mínimo 6.31:1) y 6 pares de borde/foco contra superficies
(mínimo 3.39:1), según luminancia relativa WCAG. También se verificó renderizado
en Chrome a 1280/768 px y navegación mediante eventos de teclado de navegador;
resultados y limitaciones en `validation.md`.

Pendiente de revisión humana: aprobar estilo, jerarquía y legibilidad. La
conformidad final del producto requiere
medición y pruebas del frontend implementado, no se deduce de esta maqueta.
