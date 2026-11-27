# SPEC-036 — HU-35 · Plan técnico

Issue: #95 · Rama: `feature/hu-35-edicion-iterativa` (apilada sobre HU-33) · Destino PR: `main`.

## Decisiones que fija este plan

1. **Identificación de la pieza previa (S10)**: el `solicitud_id`. Es el id que `/generar` ya
   devuelve en `X-Solicitud-ID` y `X-Registro-ID`, ya ligado a un dueño por HU-53 y ya usado
   por `/generaciones/{id}` y `/registros/{id}`. El cliente **no** reenvía el programa: el
   servidor toma la última versión verificada de su propio almacén, así que una edición nunca
   puede partir de un programa ajeno ni inventado.
2. **Prompt de edición (S9, contrato de HU-33 intacto)**: archivo nuevo
   `prompts/editor-v1.txt` con su entrada `id = "editor"`, `version = 1`, `vigente = true` en
   `prompts/manifest.toml`. `planner-v1` no se toca; el cargador y su puerta de CI siguen
   siendo los de HU-33.
3. **Almacén de versiones (S4, S5)**: un índice JSON por solicitud,
   `data/versiones/<solicitud_id>.json` (gitignored, como `data/registro.csv`), con escritura
   atómica y bloqueo por ruta reutilizando `persistencia_registro._publicar_bytes` y
   `_bloqueo`. Entrada por versión: `version`, `hora`, `programa`, `artefactos`, `diff`,
   `prompt`, `prompt_hash`, `causa` (sólo si la versión es una declinación registrada) y
   `usuario`. La versión 1 la escribe la generación inicial; cada edición verificada suma la
   siguiente. Una edición fallida **no** crea ni sobrescribe versiones (S6).
4. **Diff (S2)**: `versiones.diff_programas(previo, nuevo)` devuelve una lista de
   `{"ruta", "antes", "despues"}` recorriendo dicts y listas por posición, con `antes`/`despues`
   ausentes cuando la clave se agrega o se quita. Es determinista y se puede afirmar en una
   prueba; no se usa `difflib` sobre texto para no atar la salida al formato del JSON.
5. **Contrato `/v1` (sólo aditivo, S8)**: dos rutas nuevas, ninguna existente cambia de forma.
   - `POST /v1/generar/{solicitud_id}/editar`, cuerpo `{"instruccion": "<texto en español>"}`
     (y la cabecera opcional `Idempotency-Key` de HU-32). `200` con `RespuestaEdicion`
     (`version`, `programa`, `diff`, artefactos, `aviso`, `volumen_mm3`, `caja_mm`, `tiempos`,
     `prompt`) o `422` con la declinación legible y su causa de SPEC-027.
   - `GET /v1/generar/{solicitud_id}/versiones` → `RespuestaVersiones` con las versiones en
     orden ascendente, cada una con su programa y sus artefactos (S13).
   - Ambas exigen dueño: sin sesión cuando la autenticación está activa, o un id de otro
     usuario, responden `404` igual que `/registros/{id}` (HU-53).
   Los tipos del frontend y el contrato congelado se regeneran con `make api-types` y
   `make api-contract` y viajan en el commit.
6. **Registro y seguimiento (S9, S15)**: el CSV del registro **no cambia de forma**. La
   edición escribe una fila con el mismo esquema (con `prompt = editor-v1` y su hash) y la
   corrida de MLflow gana tres params: `operacion` (`generacion` o `edicion`),
   `version_pieza` y `solicitud_origen`, con lo que la proporción de ediciones verificadas se
   puede agregar sin tocar el formato persistido.
7. **Topes e idempotencia (HU-32)**: `POST /editar` pasa por `ControlUso.reservar` y
   `reservar_idempotencia` igual que `/generar`, y el costo medido se imputa con
   `medir_solicitud`.
8. **UI fuera de alcance**: el historial en la interfaz es SPEC-038; aquí sólo se regeneran
   los tipos, sin cambios visuales.
9. **SSE fuera de alcance**: la edición es síncrona (JSON). La cola y el worker no cambian;
   el endpoint reutiliza el mismo registrador y la misma medición que la ruta JSON.

## Interfaces congeladas (las consume la API y las pruebas)

`src/m2_cad/versiones.py`

```python
RUTA_VERSIONES = Path("data/versiones")          # M2_VERSIONES_DIR lo sobreescribe

def ruta_versiones() -> Path                      # directorio efectivo
def diff_programas(previo: dict, nuevo: dict) -> list[dict]
def registrar_version(solicitud_id: str, *, usuario: str, programa: dict,
                      artefactos: list[str], prompt: str, prompt_hash: str,
                      diff: list[dict] | None = None, causa: str | None = None,
                      version: int | None = None, directorio: Path | None = None) -> dict
def leer_versiones(solicitud_id: str, *, directorio: Path | None = None) -> list[dict]
def ultima_version(solicitud_id: str, *, directorio: Path | None = None) -> dict | None
def nueva_version(versiones: list[dict]) -> int   # max+1, 1 si está vacío
class ErrorVersiones(ValueError)
```

`validar_solicitud_id` rechaza cualquier id que no sea un uuid hexadecimal (sin `/`, `..` ni
rutas), para que el índice no salga nunca de su directorio.

`src/m2_cad/pipeline.py`

```python
PROMPT_EDICION = prompts.cargar("editor")         # Prompt de edición

def editar_pieza(programa_previo: dict, instruccion: str, *,
                 planificar: Callable[[str], dict] | None = None,
                 directorio: Path = RUTA_SALIDA,
                 control: ControlGeneracion | None = None,
                 medir_uso: Callable[[dict], None] | None = None) -> ResultadoPieza
```

Reutiliza `extraer_programa`, `validar_catalogo`, `verificar_programa`, `construir_pieza` y
`generar_pieza`'s salida (los mismos caminos de declinación con causa de SPEC-027). El mensaje
al modelo lleva el programa anterior y la instrucción; el sistema es `PROMPT_EDICION.texto`.
`_respuesta_modelo` gana el parámetro `sistema=PROMPT_SISTEMA` para no duplicar la llamada.

## Pruebas

| Archivo | Qué afirma |
|---|---|
| `tests/test_versiones.py` | diff de cambios, altas y bajas; índice en orden; versión nueva = max+1; ids inválidos rechazados; archivo corrupto con `ErrorVersiones`. |
| `tests/test_edicion.py` | edición verificada con modelo simulado (programa nuevo, artefactos en un directorio nuevo); edición que rompe la verificación → declinación con causa y versión previa intacta; el prompt usado es `editor-v1`. |
| `tests/test_api_edicion.py` | AC1 (200, diff, versión 1 conservada), AC2 (422 con causa, versiones intactas), AC3 (tres versiones en orden con programa y artefactos), 404 para id ajeno o inexistente, 422 de validación del cuerpo, y que `/generar` conserva su respuesta. |
| `tests/test_prompts.py` | el manifiesto declara `planner` y `editor`, ambos cargables, y `planner-v1` no cambió. |
