# Kit de la prueba de uso simulada (HU-11)

Material para ejecutar la prueba de uso simulada de la HU-11
([spec](../../specs/006-prueba-usuarios/spec.md)). El informe de resultados se
redacta en [`../prueba-usuarios.md`](../prueba-usuarios.md).

> **Prueba simulada:** los 3 participantes son los integrantes del grupo. Sirve
> para validar el protocolo (guion, registro e informe) antes de una prueba con
> usuarios externos; sus resultados no demuestran usabilidad real. Para que la
> simulación se parezca a la prueba real,
> **cada participante actúa como usuario y otro integrante como moderador**, y el
> participante no consulta el código ni la documentación durante la sesión.

## 1. Antes de la sesión (moderador)

1. Levantar el servicio: `make up` (Vue + FastAPI con DeepSeek).
2. Abrir la interfaz en el navegador y comprobar que una placa de prueba genera STEP.
3. Tener a mano un cronómetro y la [hoja de registro](#4-hoja-de-registro).
4. Leer el consentimiento al participante y anotar su respuesta (sección 3).
5. Asignar un código anónimo: `P1`, `P2` o `P3`. **No anotar nombres.**

Rotación sugerida (nadie modera su propia sesión):

| Sesión | Participante | Moderador |
| --- | --- | --- |
| 1 | P1 | integrante de P2 |
| 2 | P2 | integrante de P3 |
| 3 | P3 | integrante de P1 |

## 2. Guion para el participante

Leer en voz alta, sin añadir pistas:

> "Vas a usar un asistente que genera piezas metálicas a partir de una descripción
> en español. Te daré 3 fichas con la pieza que necesitas. Escribe tú la
> descripción como lo harías normalmente. Yo no puedo ayudarte; si te bloqueas,
> dímelo y pasamos a la siguiente. La tarea termina cuando descargues el STEP o
> cuando el asistente te diga que no puede hacer la pieza y me expliques por qué."

Entregar las fichas **una a una**. No mostrar descripciones escritas de ejemplo:
el participante redacta la suya.

### Ficha T1 · Placa

- Placa cuadrada de 150 × 150 mm, 8 mm de espesor.
- 4 agujeros pasantes de 14 mm de diámetro, uno cerca de cada esquina (25 mm desde
  cada borde).
- Objetivo: descargar el STEP.

### Ficha T2 · Escuadra

- Escuadra de chapa doblada a 90°, espesor 3 mm, ancho 50 mm.
- Ala horizontal de 80 mm y ala vertical de 60 mm.
- 2 agujeros de 8 mm en cada ala.
- Objetivo: descargar el STEP.

### Ficha T3 · Pieza fuera del catálogo

- Engranaje recto de 40 dientes, módulo 2, espesor 15 mm.
- Objetivo: obtener el resultado del asistente. Lo esperado es una **declinación
  con motivo** (HU-05); cuenta como completada si el participante la interpreta
  bien.

## 3. Consentimiento (Ley 1581 de 2012)

Leer al participante:

> "Esta prueba evalúa el asistente, no a ti. Se registran el tiempo, si completas
> cada tarea y los problemas observados. No se guardan nombres, correos, imágenes
> ni grabaciones. Los resultados aparecen en el informe solo con un código anónimo
> (P1, P2, P3). Puedes retirarte cuando quieras. ¿Aceptas participar?"

| Código | ¿Acepta? (sí/no) | Fecha |
| --- | --- | --- |
| P1 | | |
| P2 | | |
| P3 | | |

## 4. Hoja de registro

Una fila por tarea (9 en total). El tiempo va de la entrega de la ficha hasta la
descarga del STEP o la explicación de la declinación.

**Resultado**:

- `completada`: STEP descargado (T1, T2) o declinación bien interpretada (T3).
- `con ayuda`: necesitó una pista del moderador.
- `no completada`: abandonó o el resultado es incorrecto.

| Participante | Tarea | Inicio (hh:mm:ss) | Fin (hh:mm:ss) | Tiempo (s) | Resultado | Intentos | Observaciones |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | T1 Placa | | | | | | |
| P1 | T2 Escuadra | | | | | | |
| P1 | T3 Fuera de catálogo | | | | | | |
| P2 | T1 Placa | | | | | | |
| P2 | T2 Escuadra | | | | | | |
| P2 | T3 Fuera de catálogo | | | | | | |
| P3 | T1 Placa | | | | | | |
| P3 | T2 Escuadra | | | | | | |
| P3 | T3 Fuera de catálogo | | | | | | |

## 5. Problemas observados

Anotar cada problema en cuanto aparezca. Escala de gravedad:

- **Alta**: impide completar la tarea.
- **Media**: la retrasa o exige varios intentos.
- **Baja**: molestia o confusión menor.

| ID | Participante | Tarea | Descripción | Gravedad |
| --- | --- | --- | --- | --- |
| PR1 | | | | |
| PR2 | | | | |
| PR3 | | | | |

## 6. Al terminar

1. Pasar la hoja de registro y los problemas al informe
   [`../prueba-usuarios.md`](../prueba-usuarios.md).
2. Comprobar que no aparece ningún nombre ni dato personal.
