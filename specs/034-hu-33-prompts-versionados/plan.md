# SPEC-034 — HU-33 · Plan técnico

Issue: #93 · Rama: `feature/hu-33-prompts-versionados` · Destino PR: `main`.

## Contrato estable del prompt versionado (lo que consume HU-35)

HU-35 (edición iterativa) y SPEC-053 (A/B) necesitan una identidad de prompt que no cambie
de forma. Se congela así:

```text
prompts/
├── manifest.toml          # declaración: id, version, archivo, sha256, descripcion, vigente
└── planner-v1.txt         # el texto, byte a byte igual a PROMPT_SISTEMA actual

src/m2_cad/prompts.py      # único cargador; nada más lee archivos de prompts
    PROMPT_VIGENTE = "planner"
    @dataclass(frozen=True) Prompt: id, version, archivo, sha256, texto
        .etiqueta -> "planner-v1"      # lo que se persiste: id y versión en un token
    cargar(id_prompt=PROMPT_VIGENTE, *, raiz=None) -> Prompt   # valida el hash
    listar(*, raiz=None) -> list[Prompt]
    verificar(*, raiz=None) -> list[str]   # errores de manifiesto integridad
    sha256_texto(texto) -> str
    ErrorPrompt(ValueError)
```

- `Prompt.etiqueta` (`planner-v1`) es la **versión de prompt** que viaja al registro y a
  MLflow; `Prompt.sha256` es el hash del contenido. HU-35 puede pedir `cargar("planner")`,
  escribir `planner-v2.txt`, subir `version` a 2 en el manifiesto y cambiar `vigente`; nada
  más del pipeline depende del nombre del archivo.
- El **manifiesto** es la fuente de la verdad de versiones: una versión por entrada, un solo
  `vigente = true` por `id`, `sha256` obligatorio con formato hexadecimal de 64 caracteres.
- El texto de `planner-v1.txt` es **idéntico** a `PROMPT_SISTEMA` de hoy (RNF-2): la
  migración no cambia lo que recibe el modelo.

## Piezas

| Pieza | Qué hace |
|---|---|
| `prompts/manifest.toml` + `prompts/planner-v1.txt` | Prompt vigente como artefacto versionado con id, versión y hash. |
| `src/m2_cad/prompts.py` | Cargador y validador; sin red, sin dependencias nuevas (`tomllib` y `hashlib`). |
| `src/m2_cad/pipeline.py` | `PROMPT_VIGENTE = prompts.cargar()` y `PROMPT_SISTEMA = PROMPT_VIGENTE.texto`; `_respuesta_modelo` sigue usando `PROMPT_SISTEMA`. |
| `src/m2_cad/registro.py` | Columnas aditivas `prompt` y `prompt_hash`, migradas con el mismo mecanismo que `usuario` (HU-53) y `causa` (HU-26); `SIN_PROMPT = "no aplica"` cuando la solicitud no llegó al modelo (SPEC-004 AC3: sin vacíos). |
| `src/m2_cad/api.py` | `_preparar_medicion` anota `prompt` y `prompt_hash`; `medir_solicitud` los registra como params de MLflow; las altas del registro los leen de `medido`. |
| `src/m2_cad/worker.py` | El alta del trabajo declinado/terminado pasa los mismos valores. |
| `scripts/verify_prompts.py` | CLI fina sobre `prompts.verificar()`; exit 0/1 con mensaje en español que nombra archivo, versión declarada y los dos hashes. |
| `Makefile` | `prompts-check` y `check: ... prompts-check` (offline y barato, como `lint`). |
| `.gitlab-ci.yml` | El job `lint` corre `make prompts-check`, para que el espejo también lo exija. |
| `tests/test_ci_parity.py` | Vigila que los dos pipelines corran el chequeo. |

## Formatos consumidos que cambian (dicho explícitamente)

- **Registro CSV**: pasan de 10 a 12 columnas con `prompt` y `prompt_hash` al final. Un CSV
  anterior se migra en la próxima escritura con los mismos valores por defecto
  (`"no aplica"`); el mismo mecanismo de `_asegurar_columnas` que ya migró `usuario` y
  `causa`, más `persistencia_registro.restore` aceptando snapshots anteriores.
- **MLflow**: dos params nuevos (`prompt`, `prompt_hash`) por corrida de generación. Son
  aditivos: ninguna corrida vieja se reescribe.
- **Contrato `/v1`: NO cambia.** Ni el cuerpo, ni cabeceras, ni códigos: los tipos del
  frontend no se regeneran (`make api-types-check` y `make api-contract-check` deben seguir
  verdes sin tocar `frontend/src/generated/api.ts` ni `contracts/openapi-v1.json`).

## Chequeo de CI (AC2)

`make prompts-check` recorre el manifiesto y falla con un mensaje en español si:

1. el `sha256` declarado no coincide con el contenido del archivo (cambio sin subir versión),
2. hay dos entradas con el mismo `id` y `version`,
3. un `id` no tiene exactamente una entrada `vigente = true`,
4. falta el archivo o su `sha256` no tiene el formato esperado.

El mismo `verificar()` se ejercita en `tests/test_prompts.py` sobre una copia temporal
mutada, así que el fallo está probado sin tocar los archivos reales. Corre en GitHub dentro
de `make check` y en el espejo dentro del job `lint`: paridad vigilada por prueba.

## Pruebas

- `tests/test_prompts.py` (AAA, sin red): AC3 de punta a punta (pipeline carga por id, hash
  del archivo, fila del registro con `prompt` y `prompt_hash`); manifiesto real válido;
  mutación de contenido en copia temporal → error con archivo y hashes; versión duplicada y
  sin vigente → error; `PROMPT_SISTEMA == cargar().texto` (RNF-2).
- `tests/test_registro.py`: columnas nuevas y migración desde 8, 9 y 10 columnas.
- `tests/test_api_seguimiento.py`: la corrida de MLflow lleva `prompt` y `prompt_hash`, y la
  fila del registro los mismos valores (AC1).
- `tests/test_ci_parity.py`: los dos pipelines ejecutan `make prompts-check`.
