# SPEC-012 · HU-03 — Plan técnico de la traducción ES→EN

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #27). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-012
- **Historia**: HU-03 (issue #3)
- **Responsable**: Juan Camilo Pérez (`JuanC0319`)
- **Rama**: `feature/hu-03-traduccion`
- **PR**: #27 (fusionado el 2026-11-10, commit `dbe7dca`); antecedente PR #15
- **Estado**: Implementada y luego retirada por HU-14 (SPEC-008)
- **Documentos**: [`spec.md`](./spec.md) · [`tasks.md`](./tasks.md)

El código descrito ya no existe en la rama actual. Para leerlo:
`git show dbe7dca:src/m2_cad/traduccion.py` y `git show dbe7dca:tests/test_translate.py`.

## Diseño técnico

Módulo único `src/m2_cad/traduccion.py` (120 líneas):

1. `traducir_solicitud(texto)` valida la entrada (no vacía, ≤ 1000 caracteres) y lee
   `GEMINI_API_KEY`.
2. `_proteger_valores(texto)` reemplaza cada coincidencia de `PATRON_VALOR`
   (`\d+(?:[.,]\d+)?(?:[ \t]*(?:mm|cm|kg|g|m)\b)?`, sin distinguir mayúsculas) por
   `__CADVAL_N__` y guarda el valor original.
3. `_consultar_gemini(texto_protegido, clave)` hace `POST` a
   `…/v1beta/models/gemini-3.5-flash-lite:generateContent` con `temperature: 0`,
   cabecera `x-goog-api-key` y tiempo de espera de 8 s; une las partes no `thought`.
4. `_restaurar_valores(traduccion, original, valores)` exige el mismo multiconjunto de
   marcadores, los sustituye por los valores originales y compara el multiconjunto de
   números (`PATRON_NUMERO`) entre original y traducción.

Integración posterior (HU-04, commit `cff998f`): `pipeline.generar_pieza(texto,
traducir=traducir_solicitud)` traducía y pasaba el inglés a `planificar`;
`ResultadoPieza.traduccion` exponía el texto traducido. `api.procesar_con_pipeline`
mapeaba `ErrorTraduccion` a HTTP 503.

## Decisiones

- **Marcadores reversibles en lugar de confiar en el modelo**. *Porqué*: el LLM no puede
  alterar una cifra que no ve; la restauración es determinista.
- **Doble control (marcadores + números)**. *Porqué*: detectar cifras añadidas por el
  modelo aunque conserve todos los marcadores (prueba pedida en la revisión del PR #15).
- **`urllib` de la biblioteca estándar**. *Porqué*: no añadir el SDK de Gemini como dependencia.
- **Error tipado `ErrorTraduccion(RuntimeError)`**. *Porqué*: que la API distinga un
  fallo del servicio externo (503) de una entrada inválida (`ValueError`).

## Contratos

```python
traducir_solicitud(texto: str) -> str           # ValueError | ErrorTraduccion
class ErrorTraduccion(RuntimeError)
_proteger_valores(texto: str) -> tuple[str, dict[str, str]]
_restaurar_valores(traduccion: str, original: str, valores: dict[str, str]) -> str
```

Entorno: `GEMINI_API_KEY`. Constantes: `MODELO`, `TIEMPO_ESPERA = 8`, `LONGITUD_MAXIMA = 1000`.

## Riesgos

- **Dependencia de un servicio externo** en la ruta crítica: sin clave o sin red, ninguna
  pieza se genera (503).
- **Latencia acumulada**: la traducción se suma a la planificación; el AC3 no se midió.
- **Decimales con coma**: se conservan tal cual (`12,5 mm`), contra el ejemplo del
  issue (`12.5 mm`); el planificador en inglés recibe notación mixta.
- **Cobertura del patrón**: unidades fuera de la lista (`in`, `°`, `M8`) no se protegen.
- **Datos personales**: el texto completo se envía a un tercero.

Estos riesgos se resolvieron con el retiro: HU-14 elimina el salto de traducción y
envía el español directamente a DeepSeek.

## Alternativas descartadas

- **Pedir al modelo que conserve números sin marcadores**: no verificable.
- **Traducción por reglas o diccionario**: no cubre la sintaxis libre de las solicitudes.
- **Mantener la traducción con DeepSeek** (decisión de HU-14): el modelo planifica
  desde español, así que el paso añadía latencia, costo y un punto de fallo sin beneficio.

## Estrategia de pruebas

- `tests/test_translate.py` (16 casos, sin red): importación del módulo, protección y
  restauración de medidas (incluido `12,5 mm`, `8mm`, `1.25 cm`, `2 m`, `3 kg`),
  marcador faltante, entrada vacía, entrada > 1000 caracteres, ausencia de clave, cifras
  añadidas por el modelo, error de red (`urlopen` simulado) y flujo completo con
  `_consultar_gemini` simulado.
- La revisión del PR #15 midió 64 % de cobertura en `traduccion.py`; los 4 casos
  añadidos en el PR #27 llevaron la suite a 80,33 %.
- No hubo prueba de integración contra Gemini real ni medición de latencia.
