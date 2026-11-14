# Informe de la prueba de uso simulada (HU-11)

> ⚠️ **SIMULADO.** Este informe recoge una prueba **simulada** por los integrantes
> del grupo para validar el protocolo. Los tiempos, resultados y problemas son
> **datos ilustrativos, no mediciones de sesiones reales**, y **no son evidencia de
> usabilidad**.
>
> Kit de ejecución: [`prueba-usuarios/kit.md`](prueba-usuarios/kit.md) ·
> Spec: [`specs/006-prueba-usuarios`](../specs/006-prueba-usuarios/spec.md).

## 1. Contexto

- **Fecha:** 2026-11-14 (simulación).
- **Modalidad:** simulación de escritorio con el kit; no hubo sesiones moderadas.
- **Versión de referencia:** rama `develop` (servicio con `make up`).
- **Participantes simulados:** 3 (P1, P2, P3), integrantes del grupo con experiencia
  previa en CAD. No se registran datos personales.

### Alcance

La prueba es **simulada**. Su objetivo es validar el kit, la hoja de registro y
este informe: que las fichas se entienden, que la hoja permite calcular el umbral y
que los problemas se pueden priorizar. Los resultados **no** sirven para afirmar
que el producto es usable por su público objetivo; para eso hace falta la prueba
con usuarios externos (trabajo futuro).

## 2. Datos personales (AC5)

No aplica consentimiento formal: no hubo sesiones con terceros. Los participantes
se identifican solo con códigos (P1–P3) y el informe no contiene nombres, correos,
imágenes ni grabaciones.

## 3. Resultados por tarea (AC1, AC3) · SIMULADO

Resultado · tiempo en segundos · intentos.

| Participante | T1 Placa | T2 Escuadra | T3 Fuera de catálogo |
| --- | --- | --- | --- |
| P1 | completada · 112 s · 1 | completada · 185 s · 2 | completada · 74 s · 1 |
| P2 | completada · 98 s · 1 | **con ayuda** · 262 s · 3 | completada · 81 s · 1 |
| P3 | completada · 135 s · 2 | completada · 204 s · 2 | completada · 66 s · 1 |

En T3 (engranaje recto de 40 dientes), "completada" significa que el asistente
declinó con motivo y el participante explicó correctamente por qué (HU-05).

## 4. Umbral de éxito (AC2) · SIMULADO

- **Tareas completadas sin ayuda:** 8 / 9
- **Umbral:** ≥ 7 / 9
- **Veredicto (simulado):** cumple. El protocolo permite calcular el umbral sin
  ambigüedad.

| Tarea | Tiempo medio (s) | Tiempo mínimo (s) | Tiempo máximo (s) |
| --- | --- | --- | --- |
| T1 Placa | 115 | 98 | 135 |
| T2 Escuadra | 217 | 185 | 262 |
| T3 Fuera de catálogo | 74 | 66 | 81 |

## 5. Problemas por gravedad (AC4) · SIMULADO

Ordenados de mayor a menor gravedad (escala del kit: alta impide completar, media
retrasa o exige varios intentos, baja es una molestia menor).

| ID | Gravedad | Descripción | Participantes afectados | Estado |
| --- | --- | --- | --- | --- |
| PR1 | Alta | En la escuadra, la descripción no aclara en qué posición van los agujeros de cada ala; la pieza sale con los agujeros donde el participante no esperaba y necesita pista del moderador. | P2 (P1, P3 con reintento) | Documentado |
| PR2 | Media | Mientras se genera la pieza, el progreso por etapas no indica cuánto falta; el participante duda si el sistema sigue trabajando y reenvía la solicitud. | P1, P3 | Documentado |
| PR3 | Media | En la placa, "agujeros en las esquinas" sin distancia al borde produce una posición distinta a la de la ficha y obliga a reintentar. | P3 | Abierto |
| PR4 | Baja | El mensaje de declinación del engranaje explica el motivo, pero no sugiere qué familias sí admite el catálogo. | P1, P2 | Abierto |

### Los 2 problemas más graves

1. **PR1 · Posición de agujeros en la escuadra (documentado).** La causa es una
   descripción ambigua más que un fallo del sistema. Propuesta: mostrar en la
   interfaz un ejemplo de descripción de escuadra con la posición de los agujeros
   y, en la vista 3D, resaltar las cotas de los agujeros para detectar el error
   antes de descargar el STEP.
2. **PR2 · Incertidumbre durante la espera (documentado).** Propuesta: mostrar la
   etapa actual con un indicador de "en curso" y deshabilitar el botón de envío
   mientras la solicitud está en proceso para evitar envíos duplicados.

## 6. Conclusión

La simulación valida el protocolo: las 3 fichas cubren el catálogo (placa,
escuadra) y la declinación (engranaje), la hoja de registro permite calcular el
umbral de 7/9 y los tiempos, y la escala de gravedad permite priorizar los
hallazgos. Los problemas listados son **hipótesis simuladas** que la prueba real
debe confirmar o descartar.

**Próximo paso:** ejecutar la prueba con 3 usuarios externos con experiencia en
CAD usando este mismo kit (trabajo futuro).
