# Plan de implementación · HU-46 (SPEC-047)

## Contexto

SPEC-047 depende de SPEC-045 (baseline y replay del banco, PR #151) y de SPEC-027
(causas cerradas de declinación). La rama `feature/hu-46-alertas-regresion` se crea desde
`feature/hu-44-banco-ci-replay` mientras #151 está en revisión; el PR final apunta a `main`
y, al fusionarse #151, el diff queda limitado a los archivos de HU-46. No se fusiona nada
sin aprobación.

La comparación debe funcionar sobre datos ya producidos: el resumen JSON y el CSV del banco
en replay (o de la corrida real programada). No llama al modelo, no usa GPU y no necesita red.

## Decisiones técnicas

1. **Módulo puro**: `src/m2_cad/alertas.py` contiene el esquema v1 del baseline, la carga
   validada del resumen/CSV, el cálculo de métricas y el comparador. Sin efectos secundarios:
   la CLI decide si escribe y con qué código sale.
2. **Métricas comparadas** (RF-2): `acierto`, `declinaciones_correctas` y
   `errores_silenciosos`. Las dos últimas se derivan del CSV por caso:
   - declinación correcta: `esperado = declinar` y `correcto = true`;
   - error silencioso: `correcto = false` y `estado = construida` (pieza aceptada que no
     cumple la referencia, HU-07).
   Los deltas son absolutos y se comparan contra umbrales **versionados** en el baseline
   (RNF-3), nunca escritos en el código.
3. **Causa estructurada** (RF-3): `banco.py` añade `causa` al CSV por caso; el comparador
   valida cada valor con `declinacion.normalizar()` y lo muestra junto a la familia en los
   casos cambiados. No clasifica texto libre.
4. **Baseline explícito** (RF-5): `data/alertas_baseline.json` incluye `id`, métricas,
   casos por ID, umbrales y un bloque `actualizado` con quién, cuándo, desde qué corrida y
   por qué, más un `historial` append-only. Se actualiza sólo con
   `--actualizar-baseline --autor … --motivo … --corrida-origen …`; una comparación normal
   nunca lo toca.
5. **Salidas** (RF-4): la CLI imprime un JSON con `regresion`, deltas, umbrales y casos
   cambiados; si hay regresión escribe además `outputs/alertas/<fecha>.md` con la tabla de
   métricas y el desglose. Códigos: `0` sin regresión, `1` regresión, `2` artefacto inválido.
   `--no-fail` devuelve 0 para que el workflow programado pueda abrir el issue antes de
   propagar el fallo.
6. **Integración**: `make alertas` selecciona el último JSON/CSV de un directorio. En CI corre
   justo después de `make bench-replay` con `MLFLOW_TRACKING_ENABLED=0`. En
   `banco-baseline.yml` corre con `--no-fail`, publica el JSON/Markdown como artefacto y abre
   un issue de GitHub con el resumen cuando hay regresión.
7. **Baseline inicial**: se genera a partir de la corrida replay real de HU-44 (40/40,
   `origen: referencia-banco`), con metadatos que declaran ese origen. No se presenta como
   medición del proveedor real.

## Verificación

- `tests/test_hu46_alertas.py`: AC1–AC4, ausencia de mutación del baseline, umbrales
  versionados, catálogo cerrado de causas, artefacto incompleto y script de workflow.
- Ruff, pre-commit sobre los archivos de la rama, pytest específico y suite completa con
  cobertura; contratos y frontend por si el CSV toca artefactos compartidos.
- `make alertas` sobre la corrida replay de HU-44: sin regresión, código 0, sin `.md`.
- Evidencia en `specs/047-hu-46-alertas-regresion/evidence.md` con comandos, resultados,
  límites y estado del PR. `CONSTITUTION.md` se actualiza en el mismo commit.

## Fuera de alcance

Crear el replay o la corrida real (HU-44), ajustar prompts/modelos y monitorizar latencia o
disponibilidad en producción.
