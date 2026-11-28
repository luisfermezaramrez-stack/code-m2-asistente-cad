# Spike HU-42 — del B-rep al DXF: proyección y aristas ocultas

>Fecha: 2026-11-28 · Pregunta con timebox (medio día) exigida por `specs/043-hu-42-exportacion-dxf/spec.md`.

## Preguntas

1. ¿Cómo pasa el pipeline de la proyección 3D (piezas B-rep de constraint-kit) a
   entidades DXF legibles por visores CAD estándar?
2. ¿Cómo se obtienen las aristas ocultas (*hidden lines*) para la capa
   `ARISTAS-OCULTAS`?

## Hallazgos

1. La eliminación de líneas ocultas (HLR) de OpenCascade está ya expuesta vía
   OCP y es el mismo mecanismo del exportador SVG de CadQuery
   (`cadquery/occ_impl/exporters/svg.py`): `HLRBRep_Algo` sobre el `shape`,
   `HLRAlgo_Projector` con `gp_Ax2`, y `HLRBRep_HLRToShape` entrega compuestos
   de aristas por clase. Tras fijar cámara y eje X del proyector, los puntos de
   las aristas resultantes viven en el plano 2D `(x, y)` del proyector y se
   escriben como `LWPOLYLINE` con ezdxf (2 puntos para líneas, muestreo por
   longitud para curvas).

   Dos lecciones de implementación y una de verificación:

   - Es necesario reconstruir la geometría de fondo con `BRepLib.BuildCurves3d_s`
     sobre cada compuesto (CadQuery lo hace por los *segfaults* posteriores).
   - Tras `HLRToShape` las coordenadas planas son `(x, y)` para cualquier vista:
     el spike terminó volcando `(x, z)` en la vista frontal; para superior y
     lateral eso aplana la proyección. El módulo entrega usa `(x, y)`.
   - La medida de una `DIMENSION` se lee con `Dimension.get_measurement()`, no
     con `actual_measurement`.

2. Las ocultas vienen de los compuestos espejo del HLR: `HCompound`,
   `Rg1LineHCompound` y `OutLineHCompound` (visibles: `V...Compound`). En la
   placa de prueba (40×20×6 perforada) el frontal produce 7 visibles y 53
   ocultas, que entran a `ARISTAS-OCULTAS` con `linetype="DASHED"`.

## Verificación del spike

- Pieza real del pipeline (`plate` 40×20×6), DXF R2010 con ezdxf 1.4.5.
- Reapertura con `ezdxf.audit.Auditor().run()`: 0 errores, 0 correcciones.
- Cotas con `add_linear_dim`/`add_aligned_dim`: medidas 40.0, 6.0 y 40.447 mm
  (ancho, alto y diagonal de la placa).
- Cambio de alcance: ninguno. El tamaño L previsto se sostiene; el enfoque
  declarado en la spec es viable y el veredicto quedó en `plan.md` §2.

## Evidencia

- Guion del spike: scratch fuera del repo (`/tmp/m2-spike-hu42/spike.py`),
  no versionado por regla del proyecto (no se suben artefactos desechables).
- Pruebas del módulo final: `tests/test_plano_dxf.py` (AC1, AC2, RF-1..RF-3,
  RNF-1 y RNF-3).
