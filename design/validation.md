# HU-15 · Validación de referencia y propuesta de implementación

## Comprobaciones realizadas

Se abrió el HTML local en Chrome 157.0.8103.78, sin instalar paquetes en el
proyecto. Se usaron viewport de 1280 × 1000 y 768 × 1000 píxeles CSS, escala 1.
Las capturas del primer viewport se revisaron visualmente; además se midieron
todos los elementos del documento, incluidas las variantes abiertas.

| Comprobación | 1280 px | 768 px |
| --- | --- | --- |
| Scroll horizontal | Ninguno | Ninguno |
| Elementos fuera de los límites horizontales | 0 | 0 |
| Columnas del espacio de trabajo medidas | 384 + 744 px; separación 24 px | Una columna de 705 px |
| Ancho del documento con barra vertical de 15 px | 1265 px | 753 px |
| Tabulación | Enlace de salto, descripción, seis resúmenes | Mismo orden |
| Foco | Ocho destinos visibles, contorno violeta sólido de 3 px | Igual |
| Operación | Enter/Espacio alternan variantes; Mayús+Tab retrocede | Igual |
| Enlace de salto | Enter lleva el foco a la descripción | Igual |

Las comprobaciones de teclado se ejecutaron mediante eventos de entrada reales
del navegador vía Chrome DevTools Protocol, no mediante llamadas a `element.focus()`.
Los controles deshabilitados se omiten correctamente. No se probaron acciones
de generación, cancelación o descarga: no existen en esta referencia estática.
No se afirma compatibilidad de lectores de pantalla ni de otros navegadores.
La validación anterior de contraste sigue documentada en `README.md`.

## Ajustes conservando la propuesta

No se requirió cambiar la composición. Se precisó la medida a 768 px cuando hay
barra de scroll. Se reemplazó el mensaje ambiguo «Solicitud cancelada» para una
interrupción local: ahora se distingue de la cancelación confirmada por servidor.

Los distintivos de maqueta, números de sección, nombres de tecnologías/contrato,
explicaciones de SSE, ejemplos fijos y catálogo de variantes pertenecen solo a
`design/`. No se copiarán como texto de la aplicación final.
El producto mostrará solicitud, acciones operables, etapa informada, resultado,
vista disponible, archivos y mensajes breves que ayuden a actuar. Mantendrá
«Diseño preliminar: requiere revisión profesional» y avisará cuando no disponga
de progreso. Los motivos técnicos del backend deberán traducirse a mensajes
útiles sin exponer trazas internas.

## Cancelación frente a AC3 del issue #39

El issue exige que la solicitud se pueda cancelar, pero no especifica un
protocolo de cancelación. `AbortController` o cerrar SSE solamente prueba que
el cliente dejó de recibir; un hilo, proceso o llamada al modelo puede continuar.
Por tanto, no basta ese mecanismo para declarar cumplido AC3.

Antes de implementar, definir identificación de solicitud, señal de cancelación,
propagación hasta el trabajo del servidor y confirmación observable. Puede
requerirse un canal explícito de cancelación: el endpoint y los eventos quedan
por diseñar. No se da por existente ninguno en la API actual.

La interfaz distinguirá:

- Solicitud de cancelación pendiente: «Cancelando…» mientras espera confirmación.
- Desconexión sin confirmación: «Se interrumpió la espera. El procesamiento podría
  continuar». No mostrar «Solicitud cancelada» ni afirmar liberación de recursos.
- Confirmación efectiva del backend: «Solicitud cancelada».
- Carrera con un resultado terminal ya generado: respetar la respuesta confirmada
  del servidor y evitar que una respuesta antigua sobrescriba una solicitud nueva.

Las pruebas deberán demostrar la detención del trabajo cancelable, no solo la
conexión abortada. Si una operación remota no admite detenerse, definir el límite
real, comunicarlo y resolver su compatibilidad con AC3 antes de cerrarlo.
No inventar `cancelado` como evento terminal SSE sin acordarlo: el issue define
`verificado | declinado | error`; la señal de cancelación necesita contrato propio.

## Etapas propuestas de implementación

1. **Aprobar diseño y contrato.** Fijar textos de producto, esquema SSE, orden de
   eventos, ausencia de progreso, errores, timeout, archivos y cancelación
   confirmada. Mapear cada comportamiento de `test_interfaz.py` a su prueba futura.
2. **Backend.** Instrumentar etapas reales, streaming FastAPI y ciclo de vida de
   solicitudes/cancelación; entrega segura e independiente de archivos. Probar
   eventos, desconexiones, detención real y carreras, conservando el registro.
3. **Frontend.** Vue 3 Composition API + Vite + TypeScript, reutilizando los tokens
   aprobados; flujo de solicitud, SSE, cancelar, visor y descargas. Textos finales
   útiles, sin catálogo de revisión ni progreso ficticio; pruebas Vitest/API que
   sustituyan toda la cobertura existente de UI.
4. **Integración y despliegue.** Build estático servido por FastAPI, CORS restringido
   y Compose sin pasos manuales; retirar Gradio, dependencia y puerto 7860.
5. **Aceptación.** Cobertura sin descenso, comprobaciones de calidad, SSE y
   cancelación integrados, teclado/foco/AA, ambos anchos y arranque completo de
   Compose. El resultado de esta maqueta no sustituye esas pruebas del producto.

Este documento prepara trabajo; no autoriza ni inicia la implementación.
