# SPEC-012 · HU-03 — Solicitudes en español con traducción ES→EN

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #27). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-012
- **Historia**: HU-03 (issue #3, cerrado)
- **Responsable**: Juan Camilo Pérez (`JuanC0319`)
- **Rama**: `feature/hu-03-traduccion` → `develop`
- **PR**: #27, fusionado el 2026-11-10 (commit `dbe7dca`); reenvía el PR #15 (cerrado sin fusionar por cobertura 64 % < 70 %); aprobado por `luisfermezaramrez-stack`
- **Estado**: Implementada y luego retirada por HU-14 (SPEC-008)
- **Documentos**: [`plan.md`](./plan.md) · [`tasks.md`](./tasks.md)

## Problema y contexto

El modelo de planificación de la línea base (Gemma vía constraint-kit) recibía
instrucciones en inglés, mientras que los usuarios describen las piezas en español.
HU-03 añadió `src/m2_cad/traduccion.py`: traduce la solicitud con Gemini
(`gemini-3.5-flash-lite`, API REST) y protege números y unidades con marcadores
reversibles. HU-04 la conectó al pipeline (`pipeline.generar_pieza`, parámetro
`traducir`).

**Retiro.** HU-14 (PR #43, commit `25d397d`, 2026-11-13) pasó a DeepSeek, que planifica
directamente desde español. Se eliminaron `traduccion.py`, `tests/test_translate.py`,
`ErrorTraduccion` y la variable `GEMINI_API_KEY`; la columna `traduccion` del registro
se conserva con el valor `SIN_TRADUCCION = "no aplica"` (`src/m2_cad/registro.py:43`).
Evidencia del retiro: `specs/008-hu-14-deepseek/evidence.md`.

## Historia de usuario

Texto literal de `reference/HU-Juan-Camilo-Perez.md`:

> **Como** ingeniero de instalaciones, **quiero** describir la pieza en español (por ejemplo, "placa de 120 × 120 mm, 6 mm de espesor, 4 agujeros de 12 mm en un círculo de 90 mm") y que el sistema la traduzca al inglés conservando números y unidades, **para** usar el asistente sin redactar prompts en inglés.
>
> - **AC1**: se registran texto original, traducción y tiempo.
> - **AC2**: en 20 solicitudes se conserva el 100 % de números y unidades.
> - **AC3**: traducción ≤ 5 s en el percentil 90.
> - **AC4**: `test_translate.py` cubre 10 casos o más, incluidos decimales con coma.

## Requisitos funcionales

- **RF-1**: `traducir_solicitud(texto: str) -> str` traduce una descripción CAD de español a inglés.
- **RF-2**: cifras con o sin decimales (punto o coma) y unidades `mm, cm, kg, g, m` se sustituyen por marcadores `__CADVAL_N__` antes de llamar al modelo y se restauran después.
- **RF-3**: la traducción se rechaza (`ErrorTraduccion`) si faltan, sobran o se repiten marcadores, o si el multiconjunto de números difiere del original.
- **RF-4**: entrada vacía o de más de 1000 caracteres → `ValueError`.
- **RF-5**: sin `GEMINI_API_KEY`, error de red, JSON inválido, `finishReason` distinto de `STOP` o texto vacío → `ErrorTraduccion`; la API lo convertía en HTTP 503.

## Requisitos no funcionales

- **RNF-1**: sin dependencias nuevas (cliente HTTP con `urllib`), `temperature: 0`.
- **RNF-2**: tiempo de espera de red de 8 s (`TIEMPO_ESPERA`).
- **RNF-3**: pruebas sin red real (Gemini simulado con `monkeypatch`).
- **RNF-4**: cobertura de la suite ≥ 70 % (motivo del rechazo del PR #15).

## Criterios de aceptación

Los criterios se evalúan sobre el commit `dbe7dca` y el estado previo al retiro (`25d397d^`).

**AC1 — se registran texto original, traducción y tiempo.** Brecha.
- Dado `POST /generar`, cuando se procesa una solicitud, entonces el registro debería
  guardar texto, traducción y tiempo de traducción.
- Evidencia: en `25d397d^:src/m2_cad/api.py` la llamada a `registrar` pasa
  `traduccion=""` en éxito y en error, así que la columna recibía el valor por defecto
  `"sin traduccion"`. El tiempo registrado era `latencia_ms` de toda la solicitud; no se
  midió el tiempo de traducción por separado. El PR #27 no tocó el registro.

**AC2 — en 20 solicitudes se conserva el 100 % de números y unidades.** No verificado.
- Dadas 20 solicitudes del banco, cuando se traducen, entonces se conservan todos los
  números y unidades (comparación automática).
- Evidencia: la conservación está garantizada por construcción (`_restaurar_valores`
  compara marcadores y números) y probada con 6 textos sintéticos
  (`test_proteccion_de_medidas`, `test_medidas_parametrizadas`). No se encontró una
  ejecución sobre 20 solicitudes del banco.

**AC3 — traducción ≤ 5 s en el percentil 90.** No verificado.
- Dadas solicitudes reales, cuando se mide la traducción, entonces su p90 es ≤ 5 s.
- Evidencia: no hay medición de latencia. El tiempo de espera configurado (8 s) es
  mayor que el objetivo, de modo que el código no lo impone.

**AC4 — `test_translate.py` cubre 10 casos o más, incluidos decimales con coma.** Verificado con una salvedad.
- Dado `tests/test_translate.py`, cuando se ejecuta, entonces cubre ≥ 10 casos,
  incluido «12,5 mm», y pasa en verde.
- Evidencia: 12 funciones de prueba, 16 casos con la parametrización (inspección de
  `dbe7dca:tests/test_translate.py`); PR #27 declara 16/16 y 80,33 % de cobertura; CI
  `test` en verde.
- Salvedad: el issue #3 pide `"12,5 mm" → "12.5 mm"`. La implementación conserva
  `"12,5 mm"` sin normalizar la coma y la prueba lo afirma
  (`test_traduccion_con_gemini_simulado`). La conversión a punto no se implementó.

## Fuera de alcance

- Traducción EN→ES de las respuestas.
- Unidades distintas de `mm, cm, kg, g, m` (por ejemplo `in`, `°`).
- Evaluación de calidad lingüística de la traducción.

## Métricas de éxito

| Métrica | Objetivo | Observado |
|---|---|---|
| Casos en `test_translate.py` | ≥ 10 | 16 (según PR #27 e inspección) |
| Cobertura de la suite | ≥ 70 % | 80,33 % (PR #27) |
| Números conservados en 20 solicitudes | 100 % | No medido |
| p90 de traducción | ≤ 5 s | No medido |
