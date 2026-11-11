# Banco de solicitudes · HU-02

## Decisión de cobertura

Se acuerdan 30 casos positivos: cinco por cada familia `plate`, `sheet_bracket`,
`adapter`, `flange`, `spacer` y `tornillería`. Esta selección concreta el criterio
ambiguo de seis familias del issue #2; el issue no las enumera.

`extrusion` y `pipe` siguen dentro del alcance del producto. No se consideran
negativos por su familia, aunque no estén representados en estos 30 positivos.
Los diez negativos deberán quedar fuera del alcance documentado del producto.

El banco contiene exactamente **40 solicitudes en español: 30 positivas y 10
negativas**. Los positivos tienen parámetros diferentes y referencias realmente
medidas con el motor; las pruebas no generan ni sobrescriben referencias.

## Preparación comprobada en Windows / PowerShell

`.python-version` fija Python 3.12. Se instaló Python 3.12.15 con uv, conservando
los intérpretes 3.13 existentes. Git Bash está disponible y Docker responde con
backend Linux; no se utilizó un contenedor para esta comprobación.

```powershell
uv python install 3.12
& "C:\Program Files\Git\bin\bash.exe" scripts/vendor-constraint-kit.sh
uv sync --frozen --dev --python 3.12
```

El último comando falló al compilar `python-solvespace==3.0.8`: faltan Microsoft
C++ Build Tools. Para comprobar geometría se preparó un entorno **parcial**:

```powershell
uv sync --frozen --dev --python 3.12 --no-install-package python-solvespace --no-install-package llama-cpp-python
```

No equivale a instalar todas las dependencias del proyecto. `python-solvespace`
quedó fuera por el bloqueo de compilación; `llama-cpp-python` se omitió porque
esta comprobación no requiere inferencia. Un `uv run` normal intentará sincronizar
de nuevo; para este entorno parcial se utiliza `uv run --no-sync`.

La instalación completa en Windows requiere resolver el toolchain C++ y repetir
la sincronización sin exclusiones. El procedimiento Docker del repositorio es
otra alternativa, todavía no ejecutada en esta preparación.

## Comprobación geométrica reproducible

Motor: revisión `2ed27db4d8fa821afef41103f0efc9befbf116e6`, con los dos parches
de empaquetado del script del repositorio. Versiones comprobadas:

| Componente | Versión |
| --- | --- |
| Python | 3.12.15 |
| uv | 0.13.5 |
| constraint-kit | 0.1.0 |
| CadQuery | 2.7.0 |
| cadquery-ocp | 7.8.1.1.post1 |
| build123d | 0.10.0 |
| bd_warehouse | 0.2.0 |

Desde la raíz del repositorio, ejecutar en PowerShell:

```powershell
$codigo = @'
import math
from constraint_kit.parts import plate

wp, _ = plate(
    width=40, depth=30, thick=5,
    boss_d=0, boss_h=0, bolt_d=0, bolt_circle=0, bolt_count=0,
)
solid = wp.val()
box = solid.BoundingBox()
volume = solid.Volume()
xyz = (box.xlen, box.ylen, box.zlen)
assert solid.isValid() and len(solid.Solids()) == 1
assert math.isclose(volume, 40 * 30 * 5, rel_tol=1e-10)
assert all(
    math.isclose(actual, expected, abs_tol=1e-8)
    for actual, expected in zip(xyz, (40, 30, 5))
)
print('volume_mm3:', volume)
print('bbox_xyz_mm:', xyz)
print('analytic_checks: PASS')
'@
uv run --no-sync python -B -c $codigo
```

Resultado medido: volumen **6000.0 mm³**, caja X/Y/Z **(40.0, 30.0, 5.0) mm**,
un sólido válido. Coincide con el cálculo analítico independiente del prisma
rectangular sin resalte ni agujeros. No se generaron archivos CAD ni se utilizó
inferencia, pesos del LLM o GPU.

## Comprobación de las cinco familias restantes

Se ejecutaron los cinco casos siguientes en el mismo entorno parcial. Cada uno
produjo **un único sólido B-rep válido**, con volumen y caja positivos y finitos.
Las cajas son dimensiones X/Y/Z en el sistema local del generador, sin ordenar
los ejes ni aplicar transformaciones. No se exportaron artefactos CAD.

| Familia | Tipo concreto del motor | Parámetros ejecutados |
| --- | --- | --- |
| `sheet_bracket` | `constraint_kit.parts.sheet_bracket` | `thickness=2, base_length=40, flange_length=25, width=30, bend_radius=0` |
| `adapter` | `constraint_kit.parts.adapter` | `bottom_w=40, bottom_d=40, top_d=24, height=30` |
| `flange` | `constraint_kit.parts_bd.flange` → `BlindFlange` | `nps="1", flange_class=150, kind="blind"` |
| `spacer` | `constraint_kit.parts.spacer` | `outer_d=20, bore_d=10, height=10` |
| `tornillería` | `constraint_kit.parts_bd.screw` → `SocketHeadCapScrew` | `size="M5-0.8", length=16, simple=True, fastener_type="iso4762"` |

Las dimensiones numéricas son milímetros, salvo `flange_class`, que es una clase,
y NPS, que es una designación nominal y no un diámetro real en milímetros.

### Mediciones ejecutadas

| Familia | Volumen CAD (mm³, seis decimales) | Caja CAD X/Y/Z (mm) | Contraste analítico |
| --- | --- | --- | --- |
| `sheet_bracket` | 3780.000000 | (40.0, 30.0, 25.0) | Aprobado |
| `adapter` | 29166.930055 | (40.0000002, 40.0000002, 30.0000002) | No realizado |
| `flange` | 114363.412187 | (110.0, 110.0000001, 14.7) | No realizado |
| `spacer` | 2356.194490 | (20.0, 20.0, 10.0) | Aprobado |
| `tornillería` | 477.906319 | (8.7200001, 8.7200002, 21.0000001) | No realizado |

Las pequeñas extensiones del orden de 1e-7 mm se conservan como evidencia de la
caja calculada por OpenCascade; no son dimensiones nominales nuevas. El script
imprime los valores de punto flotante completos, sin el redondeo de esta tabla.

- **Escuadra:** sin radio de doblado. La unión de los dos prismas da
  `30 * 2 * (40 + 25 - 2) = 3780 mm³`, caja `(40, 30, 25) mm`.
- **Separador:** cilindro anular, `pi/4 * (20² - 10²) * 10 = 750*pi mm³`,
  caja `(20, 20, 10) mm`. Ambos contrastes se verifican en el script con
  tolerancia relativa de volumen `1e-10` y absoluta de caja `1e-8 mm`.
- **Adaptador:** transición sólida por loft de cuadrado a círculo, sin vaciado.
  El volumen es una medición del motor, no una fórmula de cono truncado.
- **Brida:** configuración admitida por el catálogo ASME B16.5 de bd_warehouse:
  brida ciega NPS 1, clase 150. El wrapper utiliza `BlindFlange` con su cara
  predeterminada `Raised`, alineación centrada X/Y y mínima Z, sin rotación.
  Se midió la pieza de catálogo, con taladros y detalles del generador, no un
  disco aproximado. No se realizó una auditoría dimensional independiente
  contra el texto de la norma; la validez comprobada es geométrica.
- **Tornillería:** tornillo de cabeza cilíndrica con hexágono interior,
  ISO 4762, M5, paso 0.8 mm, longitud bajo cabeza 16 mm. `simple=True`
  **omite la geometría helicoidal de la rosca**; no representa una rosca
  detallada. Se conserva la representación simplificada del catálogo,
  sin sustituirla por el generador genérico `bolt`. El sentido predeterminado
  es derecho, sin rotación ni alineación adicional. El volumen registrado
  corresponde exclusivamente a esta representación; no se verificó la norma
  dimensional de forma independiente.

### Comandos reproducibles (PowerShell, raíz del repositorio)

El script imprime parámetros, tipo, validez, número de sólidos, volumen y caja.
Continúa con las demás familias si alguna falla y devuelve salida distinta de
cero si detecta errores. El identificador CLI `tornilleria` se escribe sin tilde.

```powershell
uv run --no-sync python -B scripts/verify_hu02_geometry.py sheet_bracket
uv run --no-sync python -B scripts/verify_hu02_geometry.py adapter
uv run --no-sync python -B scripts/verify_hu02_geometry.py flange
uv run --no-sync python -B scripts/verify_hu02_geometry.py spacer
uv run --no-sync python -B scripts/verify_hu02_geometry.py tornilleria
```

La ejecución efectivamente realizada utilizó un único comando para los cinco:

```powershell
uv run --no-sync python -B scripts/verify_hu02_geometry.py
```

### Limitaciones y bloqueos

Ninguno de estos cinco casos necesita `python-solvespace` ni `llama-cpp-python`.
Por ello no fue necesario ejecutar Docker ni instalar otras dependencias.
Docker Linux estaba disponible en la comprobación anterior, pero la instalación
completa en contenedor continúa siendo una alternativa no ejecutada.

Estas mediciones comprueban un caso por familia; no validan todas las variantes,
la rosca helicoidal detallada, los solvers, el pipeline completo ni inferencia.
El entorno completo sigue limitado por la ausencia de Microsoft C++ Build Tools
para `python-solvespace`; no se instaló ningún compilador.

## Formato del CSV versionado

`test_cases.csv` se guarda en UTF-8, con cabecera y exactamente cinco columnas:
`id,familia,solicitud,medidas,resultado_esperado`. Las comillas y comas de los
objetos JSON se escapan conforme a CSV; debe leerse con `csv.DictReader`, no
separando líneas por comas. Cada fila tiene una solicitud completa en español.

- `id`: identificador único `HU02-P01` a `HU02-P30` para positivos y `HU02-N01`
  a `HU02-N10` para negativos.
- `familia`: una de las seis familias acordadas o `fuera_alcance`.
- `solicitud`: geometría, orientación y representación explícitas, o tarea
  fuera del alcance documentado del producto.
- `medidas`: objeto JSON con uno de los dos esquemas siguientes.
- `resultado_esperado`: objeto JSON de referencia para positivos o la cadena
  literal `declinar` para negativos (no un objeto JSON ni un valor vacío).

Ejemplo de medidas positivas y resultado, antes del escape de CSV:

```json
{"unidad":"mm","tipo_motor":"plate","parametros":{"width":40,"depth":30,"thick":5,"boss_d":0,"boss_h":0,"bolt_d":0,"bolt_circle":0,"bolt_count":0}}
```

```json
{"volumen_mm3":6000.0,"caja_xyz_mm":[40.0,30.0,5.0]}
```

`unidad` se aplica a dimensiones físicas. Los parámetros NPS, clase ASME,
designación métrica y tipo son identificadores, no longitudes en pulgadas ni
medidas que deban convertirse directamente. `bolt_count` es un entero y `simple`
un booleano. Las claves del resultado fijan unidades: **mm³** para volumen y
**mm** para caja X/Y/Z; los ejes no se ordenan por tamaño. Los valores se guardan
con nueve decimales como máximo, conservando la tolerancia de las cajas CAD.

Ejemplo negativo:

```json
{"unidad":"mm","no_aplica":true,"motivo_esperado":"La generación Revit/BIM está fuera del alcance."}
```

No se inventan dimensiones para tareas que no definen una pieza. `no_aplica`
explica esa ausencia y `motivo_esperado` conserva el motivo de cada declinación
sin añadir una sexta columna. Todas las celdas del CSV siguen completas.

## Cobertura del banco completo

| IDs | Familia / tipo concreto | Variaciones medidas |
| --- | --- | --- |
| P01–P05 | `plate` | Cinco placas; sin agujeros, con círculos de taladros y/o resalte |
| P06–P10 | `sheet_bracket` | Cinco escuadras sin radio, con distintas alas, anchos y espesores |
| P11–P15 | `adapter` | Cinco lofts macizos rectángulo/círculo, sin giro ni vaciado |
| P16–P20 | `flange` | Ciegas NPS 1/2 clase 150, deslizante NPS 1 clase 150, con cuello NPS 1 clase 150 y ciega NPS 1 clase 300 |
| P21–P25 | `spacer` | Cinco cilindros anulares con distintos diámetros y alturas |
| P26–P30 | `tornillería` → `screw` | ISO 4762: M3-0.5×10, M4-0.7×12, M5-0.8×16, M6-1×20 y M8-1.25×25 mm |

Todos los IDs de esta tabla llevan el prefijo `HU02-`. Los cinco casos de
tornillería utilizan tornillos normalizados de cabeza cilíndrica con hexágono
interior, en representación `simple=True`, **sin hélice de rosca**. No se
sustituyeron por pernos genéricos. No se cubren todavía tuercas, arandelas ni
otras normas. Las bridas usan cara `Raised`; el motor fijado determina sus
detalles de catálogo. Se mantiene la limitación de auditoría normativa señalada
en la evidencia preliminar.

### Motivos esperados de los diez negativos

| ID | Motivo fuera del alcance |
| --- | --- |
| HU02-N01 | Cálculo y certificación de resistencia estructural |
| HU02-N02 | Verificación y certificación NSR-10 |
| HU02-N03 | Verificación y certificación RETIE |
| HU02-N04 | Generación de modelo Revit/BIM |
| HU02-N05 | Entrada por imagen y reconstrucción desde fotografía |
| HU02-N06 | Ensamblaje articulado de varias piezas |
| HU02-N07 | Reentrenamiento y entrega de pesos del LLM |
| HU02-N08 | Autenticación y gestión de usuarios |
| HU02-N09 | Concurrencia de solicitudes |
| HU02-N10 | Análisis estructural por elementos finitos y certificación de deformaciones |

Estos casos se clasifican respecto al **producto**, no a todas las capacidades
del motor externo. Ninguno se rechaza por pertenecer a `extrusion` o `pipe`.

## Regeneración y contraste sin LLM

`scripts/generate_hu02_dataset.py` contiene los 30 conjuntos de parámetros fuente,
los textos y los diez motivos negativos. No contiene volúmenes precalculados.
Invoca los generadores deterministas del motor y mide cada sólido de nuevo,
incluidos los casos coincidentes con las comprobaciones preliminares anteriores.

Antes de medir verifica Python 3.12, la revisión Git del motor y las cinco
versiones CAD de la tabla de entorno. La primera generación completó **30/30
sólidos válidos y 15/15 contrastes analíticos**. Los demás casos se respaldan por
medición B-rep; no se les asignó una fórmula aproximada de volumen.

Contrastes independientes aplicados a cada conjunto de parámetros:

- Placas: `width*depth*thick + pi*boss_d²*boss_h/4
  - bolt_count*pi*bolt_d²*thick/4`. Los taladros quedan dentro de la placa,
  separados entre sí y sin invadir el resalte; esto también se valida.
- Escuadras: `width*thickness*(base_length+flange_length-thickness)`.
- Separadores: `pi*(outer_d²-bore_d²)*height/4`.
- Las cajas de estas tres familias también se contrastan por álgebra; en los
  adaptadores se comprueban las extensiones de los perfiles y su altura.
- Para lofts, bridas y tornillos no se afirma un contraste independiente de
  volumen; las referencias proceden de los sólidos efectivamente construidos.

**Reproducir y comparar sin escribir** (comportamiento predeterminado):

```powershell
uv run --no-sync python -B scripts/generate_hu02_dataset.py --check
```

Se comparan también IDs, familias, solicitudes y parámetros con las fuentes.
La tolerancia de reproducción es `rel_tol=1e-8`, `abs_tol=1e-6 mm³` para volumen
y `abs_tol=2e-6 mm` para caja. No es la tolerancia ±2 % de la futura evaluación
del asistente. Una discrepancia hace fallar el comando y no modifica el CSV.

**Regenerar deliberadamente**, después de revisar cualquier cambio de casos:

```powershell
uv run --no-sync python -B scripts/generate_hu02_dataset.py --write
```

Solo `--write` reemplaza el CSV y únicamente después de construir y validar
los 30 positivos y el contrato completo. Revisar el diff y tramitar cualquier
cambio posterior mediante pull request a `develop`.

## Pruebas del banco frente a evaluación del asistente

```powershell
uv run --no-sync python -B -m pytest tests/test_dataset.py -p no:cacheprovider
uv run --no-sync python -B -m pytest --cov=src/m2_cad --cov-report=term-missing
uv run --no-sync ruff check src tests scripts/generate_hu02_dataset.py scripts/verify_hu02_geometry.py
```

El contrato en `src/m2_cad/dataset.py` solo usa la biblioteca estándar.
`tests/test_dataset.py` verifica estructura, reparto, unicidad, completitud,
tipos, unidades, finitud, coherencia geométrica, referencias analíticas y
rechazo de datos corruptos. Incluye una validación en un intérprete con `-S`
(sin site-packages) para comprobar su independencia del motor CAD y del LLM.
Pytest requiere pytest, pero no CadQuery, GPU ni pesos para estas pruebas.
Las pruebas no llaman al regenerador ni escriben el CSV.

**HU-02 valida el banco y sus referencias. HU-07 sigue pendiente:** aquí no se
ha medido la tasa de construcción/declinación del LLM, ni su latencia o calidad.
Los treinta éxitos geométricos son de los generadores deterministas con
parámetros explícitos, no treinta solicitudes resueltas mediante inferencia.

### Resultado de la verificación de implementación

- Generación CAD y reproducción posterior sin escritura: **30/30** sólidos
  válidos, **15/15** contrastes analíticos y **10/10** negativos completos.
- Pruebas específicas del banco: **102 aprobadas**, incluida la validación sin
  site-packages; no se regeneró el CSV durante pytest.
- Suite completa: **144 aprobadas**, cobertura global **95.51 %** y cobertura
  de `src/m2_cad/dataset.py` **100 %** (cobertura de líneas).
- Se corrigió una comparación de ruta preexistente en
  `tests/test_registro.py`: `.as_posix()` mantiene la misma expectativa y permite
  ejecutar la prueba en Windows sin cambiar el comportamiento del registro.
- Sin cambios de dependencias, pesos del LLM, GPU ni instalación de compiladores.
