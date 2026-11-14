# SPEC-016 · HU-07 — Plan técnico del reporte del banco

- **ID**: SPEC-016 · **Historia**: #7 · **Responsable**: Carlos Eduardo Trujillo
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## 1. Diseño técnico

Se extiende `src/m2_cad/banco.py` sin romper su contrato actual:

1. **Directorio persistente opcional**: `main` acepta `--conservar-step`. Con la opción,
   cada caso se construye en `outputs/banco/<modelo>-<marca>/<id>/` en lugar del
   `TemporaryDirectory`; sin ella, todo sigue como hoy (RNF-3).
2. **Clasificación**: `evaluar_caso` añade `error_silencioso` (bool) y `step` (ruta o
   vacío) al registro. `error_silencioso = estado == "construida" and not correcto`,
   que cubre positivas fuera de tolerancia y negativas construidas.
3. **Agregación**: nueva función pura `resumir_por_familia(registros) -> dict` con
   `conformes`, `positivas`, `declinaciones_correctas`, `negativas` y
   `errores_silenciosos` por familia y total.
4. **Reporte**: nueva función pura `reporte_markdown(registros, resumen, por_familia,
   *, modelo, commit, fecha) -> str`. `main --reporte RUTA` la escribe en `docs/`.
5. **Comando**: `make bench-report` =
   `uv run python -m m2_cad.banco --conservar-step --reporte docs/reporte-banco.md`.

## 2. Decisiones

| Decisión | Porqué |
| --- | --- |
| Extender `banco.py` en vez de un script nuevo | Reutiliza `evaluar_caso`, `ContadorUso` y el seguimiento de HU-16 sin duplicar la clasificación. |
| Funciones puras para agregar y redactar | Se prueban sin red ni CAD, con registros sintéticos. |
| "Registro" del caso = fila del CSV + `run_id` de MLflow | El banco no pasa por la API, así que no escribe en `data/registro.csv`; el CSV por caso y la corrida hija son su registro real. |
| Opciones nuevas apagadas por defecto | `make bench` y las pruebas de HU-14/HU-16 no cambian (RNF-3). |
| Reporte versionado, STEP no | Los STEP pesan y se regeneran; el reporte es la evidencia. |

## 3. Contratos

- `evaluar_caso(...)` → registro actual + `error_silencioso: bool`, `step: str`.
- `resumir_por_familia(registros: list[dict]) -> dict[str, dict[str, int]]` con la
  clave `"total"`.
- `reporte_markdown(...) -> str`: tabla por familia con metas, tabla por caso (id,
  familia, estado, correcto, error silencioso, STEP, `run_id`) y sección de fallos.
- CLI: `--conservar-step` y `--reporte PATH` (ambas opcionales). `CAMPOS` del CSV gana
  `error_silencioso` y `step` al final, sin reordenar las columnas existentes.

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Romper el CSV que consumen HU-14/HU-16 | Las columnas nuevas van al final; prueba que fija el orden previo. |
| Costo y tiempo de 40 llamadas a DeepSeek | Una corrida, más una repetición solo si una meta falla (AC4). |
| Rutas absolutas o datos personales en el reporte | Rutas relativas al repo; las solicitudes del banco no contienen datos personales (HU-02). |

## 5. Alternativas descartadas

- **Notebook de análisis**: la rúbrica no acepta notebooks como entrega.
- **Reporte solo en MLflow**: AC5 exige el reporte en `docs/`; MLflow queda como complemento.
- **Pasar el banco por la API para usar `data/registro.csv`**: añade HTTP y concurrencia sin aportar al criterio.

## 6. Estrategia de pruebas

En `tests/test_banco.py` (AAA, sin red ni GPU, generador simulado como en las pruebas existentes):

- `error_silencioso` para positiva fuera de tolerancia, negativa construida y
  declinación correcta (tres casos).
- `resumir_por_familia` con registros sintéticos de 2 familias y el total.
- `reporte_markdown` contiene las metas, el estado cumple/no cumple y los enlaces.
- `--conservar-step` deja el STEP en la ruta declarada; sin la opción, no queda nada en `outputs/`.
- Regresión: el CSV sin opciones nuevas conserva el orden de columnas previo.
