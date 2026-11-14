# HU-15 · Integración con HU-14 (PR #46)

## Punto de partida y resolución

Árbol limpio confirmado en `feature/39-hu-15-vue-fastapi-sse`, HEAD `e0c013e`.
Se creó el respaldo local `backup/hu15-pre-integration-e0c013e`, se ejecutó
`git fetch origin` y se fusionó `origin/develop` (`c9ccab1`) con `--no-commit`
para revisar cada conflicto. No se aplicó ni eliminó el stash HU-07.

| Conflicto | Resolución individual |
| --- | --- |
| `CONSTITUTION.md` (add/add) | Conservar gobernanza/estructura de develop y actualizar runtime a DeepSeek directo + Vue/FastAPI/SSE |
| `Makefile` | Conservar banco y comandos heredados opt-in de HU-14, añadir frontend/check y requisito de build para pytest |
| `README.md` | Mantener configuración DeepSeek, banco y evidencia HU-14; integrar Vue/SSE y retirar requisitos normales de Gemini/GPU/Gradio |
| `docker-compose.yml` | DeepSeek externo y un solo servicio Vue/FastAPI, sin llama ni Gradio en el arranque normal |
| `api.py` | JSON y SSE comparten configuración del modelo de HU-14; SSE registra `SIN_TRADUCCION` (`no aplica`) |
| `pipeline.py` | Español directo a `planificar_con_llm`, sin importar traducción; conservar puntos seguros y eventos SSE, y la caja envolvente previa a exportación de HU-14 |

Se revisaron también los merges automáticos: se conservaron `banco.py`,
`registro.py`, pruebas HU-14, eliminación de `traduccion.py` y sus pruebas,
parámetros/prompt/errores de DeepSeek y la evidencia HU-14. No se usó una
selección general `ours`/`theirs` ni se reincorporó el cliente anterior del modelo.

Las etapas ahora significan validación de texto → planificación directa desde
español → resultado. El esquema SSE y de artefactos consumido por Vue permanece
compatible; no se añaden eventos de traducción ni progreso ficticio. La UI
continúa informando errores y distingue detención local de remota.

## Ajustes derivados

- SSE reconoce `DEEPSEEK_API_KEY` o `LLM_API_KEY` sin exigir `LLM_BASE_URL`, igual
  que la API JSON de HU-14. La URL por defecto y modelo siguen siendo los de HU-14.
- Nuevas pruebas de integración usan el adaptador SSE y pipeline/CAD reales con
  transporte DeepSeek simulado: ambas variables de clave, español intacto,
  éxito, declinación, 401, 429 y timeout; CSV `no aplica` y ausencia de clave en
  respuestas/registro. Las pruebas de cancelación ya no incluyen traducción.
- Smoke adapta su doble únicamente al modelo/planificador. **No existe ni se
  simula traducción** desde HU-14. El script elimina claves del proceso smoke;
  no se importa en el arranque normal.
- `.env.example`, AGENTS, documentación SSE y frontend alineados al contrato.
  El overlay Gemma sigue opt-in y su diagnóstico 8080 queda en loopback;
  la opción GPU remota ya no configura Gemini.

## Verificaciones ejecutadas

Todas sin llamadas a proveedores reales, descarga de pesos ni servicios de pago.

| Verificación | Resultado observado |
| --- | --- |
| Pruebas afectadas (pipeline/API/SSE/banco) | 114 aprobadas |
| Suite Python completa | 246 aprobadas, sin omisiones; cobertura 97,74 % (707 sentencias, 16 sin cubrir) |
| Vitest | 39 aprobadas en 3 archivos; dobles explícitos API/WebGL |
| TypeScript y build Vue | Correctos |
| Ruff | Correcto en src/tests/script smoke; formato corregido |
| `uv lock --check` | Correcto, sin modificar dependencias/lockfile |
| Compose base, base+Gemma, remoto y validación | Configuración válida |
| Imagen Linux integrada | Build correcto desde Dockerfile/lockfiles |
| Smoke Docker | Código 0; SSE incremental, cancelación local y descargas reales correctos |
| Arranque normal Docker + HTTP desde Windows | Saludable; health/Vue/estáticos 200, errores JSON sin HTML |

Comandos locales equivalentes a los controles de `make check`: `uv run --no-sync
ruff check src tests scripts/verify_hu15_deployment.py`, `npm --prefix frontend
test`, `npm --prefix frontend run typecheck`, `npm --prefix frontend run build`,
`uv run --no-sync pytest --cov=src/m2_cad --cov-report=term-missing -q`.
Se usó el entorno CAD Windows previamente disponible; no se afirma instalación
limpia Windows, bloqueada previamente por falta de MSVC.

Primera ejecución Ruff detectó E501 en una aserción nueva; se dividió la línea y
Ruff pasó. El formateador normalizó saltos de línea y separó un bloque de prueba.
La ejecución de pre-commit sobre todo el repositorio detectó y corrigió solo el
EOF del resumen JSON del banco importado de HU-14; no cambió sus datos.
Todos los hooks aplicables pasaron al repetirlos. `git diff --check` del merge
completo señala espacios del HTML Archify y CRLF del CSV histórico ya presentes
en develop; se conservan esos artefactos. El diff propio contra `origin/develop`
se comprueba por separado para no atribuir esos avisos a la resolución.
CadQuery/build123d emiten avisos de deprecación y Vite avisa del chunk del visor
de 644339 bytes (160,76 kB gzip), ya diferido; no hubo fallos funcionales.

### Docker repetido después de integrar

Imagen `hu15-validation-m2-cad:latest`, Linux amd64:
`sha256:a8cb653ac06116cdfbf89260824a288a1b6105bd39d131711254ca41dc8e41db`.

```powershell
docker compose -p hu15-validation build m2-cad
docker compose -p hu15-validation -f docker-compose.hu15-validation.yml run --rm --no-deps smoke
docker compose -p hu15-validation -f docker-compose.hu15-validation.yml up -d --no-deps --wait --wait-timeout 90 web
docker compose -p hu15-validation -f docker-compose.hu15-validation.yml --profile verification down
```

Smoke ejecutado dentro de la imagen, con Uvicorn y red HTTP reales:

```json
{
  "servicios": "modelo SIMULADO; sin traducción (HU-14)",
  "archivos_bytes": {"step": 12150, "glb": 32496, "csv": 77},
  "arranque_nativo": "OK",
  "sse_incremental": "OK",
  "cancelacion_local": "OK"
}
```

El campo heredado `arranque_nativo` representa aquí el proceso dentro de Docker.
Geometría CAD/verificación/exportación y descargas GET/HEAD son **reales**;
solo el modelo es **simulado**. Se verifica cabecera GLB `glTF`, terminal único,
CORS exacto, ausencia de compresión/buffering, 202 mientras el modelo simulado
bloquea y cancelación cooperativa por DELETE/desconexión.

En `web`, el CMD original arranca sin dobles. Desde Windows a loopback 18015:
`/health` y Vue 200; JS/CSS/chunk del visor 200 (82700/6146/644339 bytes);
API inexistente 404, método incorrecto 405, entrada vacía 422, generación JSON
sin clave 503, trabajo/archivo inexistente 404 y estático inexistente 404, todos
JSON sin HTML. Sin clave, SSE produce `validando → error` con `codigo_http: 503`.

El smoke conserva red interna sin puertos; web publica solo
`127.0.0.1:18015:8000`, sin credenciales ni volúmenes de usuario. Limpieza confirmada:
cero contenedores y redes por etiqueta `hu15-validation`, sin borrar volúmenes.

## Límites vigentes

La presente integración **no verifica inferencia real de DeepSeek**. HU-14 tiene
su propia evidencia histórica; no se presenta como ejecución nueva de este PR.
La cancelación es cooperativa local, sin detención inmediata de llamadas
bloqueantes ni confirmación de liberación remota. DELETE 202 no es terminal;
`cancelacion_remota_confirmada` permanece falso. El aspecto de AC3 relativo a
cancelación remota sigue pendiente; el PR continúa en borrador.

Esta evidencia no prueba renderizado del navegador, accesibilidad, instalación
limpia Windows ni arranque de la opción GPU/modelo heredada. El diagrama Archify
importado de develop sigue pendiente de regenerar para DeepSeek/Vue.
