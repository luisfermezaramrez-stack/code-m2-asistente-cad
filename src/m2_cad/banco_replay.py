"""Banco HU-02 en modo replay con respuestas grabadas y versionadas (HU-44 / SPEC-045).

Especificación: specs/045-hu-44-banco-ci-replay/spec.md
- RF-1: el proveedor se sustituye por respuestas grabadas en un artefacto JSON versionado.
- RF-2: la identidad de cada respuesta usa la clave canónica de la caché de SPEC-026 y
  declara la versión del prompt de SPEC-034 con la que se obtuvo.
- RF-3/RNF-1: CI corre el banco sin red, API key ni tokens; una grabación ausente falla
  de forma explícita antes de ejecutar el primer caso.

El artefacto `data/banco_replay.json` guarda el contenido exacto devuelto por el
proveedor, no el resultado del pipeline: la verificación DSL, la construcción B-rep
y la comparación con el banco siguen corriendo de verdad. Sólo se cambia la fuente
de la respuesta del modelo.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path

from constraint_kit import llm

from m2_cad import dataset, llm_resiliente, pipeline, prompts

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "banco_replay.json"
VERSION = 1
#: URL ficticia: hacer que el replay no pueda abrir una conexión real.
URL_REPLAY = "http://replay.invalid/v1"
ORIGENES = ("referencia-banco", "proveedor")
CLAVES_PROMPT = ("id", "version", "sha256", "etiqueta")
CLAVES_RESPUESTA = ("id", "clave", "prompt_version", "contenido")


class ErrorReplay(ValueError):
    """El artefacto de respuestas grabadas no sirve para la corrida pedida."""


def prompt_actual() -> dict:
    """Identidad del prompt vigente del planificador, tal como la ve el pipeline."""
    prompt = prompts.cargar()
    return {
        "id": prompt.id,
        "version": prompt.version,
        "sha256": prompt.sha256,
        "etiqueta": prompt.etiqueta,
    }


def cargar(ruta: Path = DEFAULT_PATH) -> dict:
    """Lee y valida el artefacto; nunca lanza una excepción de formato sin contexto."""
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ErrorReplay(f"No se encontró el artefacto de respuestas grabadas: {ruta}.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ErrorReplay(
            f"El artefacto de respuestas grabadas no es JSON válido ({ruta}): {exc}."
        ) from exc
    if not isinstance(datos, dict):
        raise ErrorReplay("El artefacto de respuestas grabadas tiene que ser un objeto JSON.")
    if datos.get("version") != VERSION:
        raise ErrorReplay(
            f"El artefacto declara version={datos.get('version')!r}; se espera {VERSION}."
        )
    if datos.get("origen") not in ORIGENES:
        raise ErrorReplay(
            f"El artefacto declara origen={datos.get('origen')!r}; sólo se admite "
            f"{', '.join(ORIGENES)}."
        )
    prompt = datos.get("prompt")
    if not isinstance(prompt, dict) or any(clave not in prompt for clave in CLAVES_PROMPT):
        raise ErrorReplay(
            f"El artefacto no declara la identidad del prompt ({', '.join(CLAVES_PROMPT)})."
        )
    actual = prompt_actual()
    for clave in CLAVES_PROMPT:
        if prompt[clave] != actual[clave]:
            raise ErrorReplay(
                f"El artefacto declara prompt.{clave}={prompt[clave]!r} pero el vigente es "
                f"{actual[clave]!r}; vuelve a grabar las respuestas con el prompt actual."
            )
    if not isinstance(datos.get("modelo"), str) or not datos["modelo"].strip():
        raise ErrorReplay("El artefacto tiene que declarar el modelo con el que se grabó.")
    respuestas = datos.get("respuestas")
    if not isinstance(respuestas, list) or not respuestas:
        raise ErrorReplay("El artefacto necesita una lista «respuestas» no vacía.")
    vistos: set[str] = set()
    claves: set[str] = set()
    for respuesta in respuestas:
        if not isinstance(respuesta, dict):
            raise ErrorReplay("Cada respuesta grabada tiene que ser un objeto JSON.")
        faltan = [clave for clave in CLAVES_RESPUESTA if clave not in respuesta]
        if faltan:
            raise ErrorReplay(f"A la respuesta grabada le falta «{faltan[0]}».")
        identificado = str(respuesta["id"])
        if identificado in vistos:
            raise ErrorReplay(f"La respuesta grabada «{identificado}» está repetida.")
        vistos.add(identificado)
        clave = str(respuesta["clave"])
        if len(clave) != 64 or set(clave) - set("0123456789abcdef"):
            raise ErrorReplay(f"La clave de «{identificado}» no es un sha256 hexadecimal.")
        if clave in claves:
            raise ErrorReplay(f"La clave de «{identificado}» está repetida en otra respuesta.")
        claves.add(clave)
        if not isinstance(respuesta["contenido"], str) or not respuesta["contenido"].strip():
            raise ErrorReplay(f"La respuesta grabada «{identificado}» no tiene contenido.")
        if respuesta["prompt_version"] != prompt["etiqueta"]:
            raise ErrorReplay(
                f"La respuesta «{identificado}» dice {respuesta['prompt_version']!r} y el "
                f"artefacto declara {prompt['etiqueta']!r}."
            )
    return datos


def clave_de(fila: dict) -> str:
    """Clave canónica de un caso del banco, igual para grabar y para replay."""
    cuerpo = pipeline.cuerpo_planificador(fila["solicitud"])
    return llm_resiliente.clave_cuerpo(cuerpo, URL_REPLAY)


def preparar(filas: list[dict], ruta: Path = DEFAULT_PATH) -> dict:
    """Valida cobertura y modelo antes de permitir una sola respuesta del replay."""
    datos = cargar(ruta)
    modelo = llm.planner_model()
    if datos["modelo"] != modelo:
        raise ErrorReplay(
            f"El artefacto se grabó con el modelo {datos['modelo']!r} y ahora está configurado "
            f"{modelo!r}; vuelve a grabar las respuestas."
        )
    por_clave = {respuesta["clave"]: respuesta for respuesta in datos["respuestas"]}
    for fila in filas:
        clave = clave_de(fila)
        respuesta = por_clave.get(clave)
        if respuesta is None:
            raise ErrorReplay(
                f"No hay respuesta grabada para «{fila['id']}»: cambió la solicitud, el prompt "
                "o el modelo. No se llama al proveedor en modo replay."
            )
        if respuesta["id"] != fila["id"]:
            raise ErrorReplay(
                f"La clave de «{fila['id']}» corresponde a la respuesta «{respuesta['id']}»."
            )
    return datos


def proveedor(datos: dict) -> Callable[..., dict]:
    """Proveedor en memoria: devuelve la grabación de la clave pedida, sin red."""

    por_clave = {respuesta["clave"]: respuesta for respuesta in datos["respuestas"]}

    def consultar(cuerpo: dict, *, url: str, timeout: float) -> dict:
        clave = llm_resiliente.clave_cuerpo(cuerpo, url)
        respuesta = por_clave.get(clave)
        if respuesta is None:
            raise ErrorReplay(
                "No hay respuesta grabada para esta petición; el replay nunca llama al modelo."
            )
        # usage vacío: el banco debe medir cero tokens y cero costo (AC1).
        return {
            "id": f"replay-{respuesta['id']}",
            "model": datos["modelo"],
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": respuesta["contenido"]},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }

    return consultar


def programa_referencia(fila: dict) -> dict:
    """Programa DSL derivado del banco, para sembrar respuestas sin llamar al modelo."""
    medidas = json.loads(fila["medidas"])
    if fila["resultado_esperado"] == "declinar":
        return {"unsupported": medidas["motivo_esperado"]}
    return {
        "parts": [
            {
                "id": "p",
                "type": medidas["tipo_motor"],
                "material": "steel",
                "params": medidas["parametros"],
            }
        ],
        "mates": [],
    }


def sembrar(filas: list[dict] | None = None, *, modelo: str | None = None) -> dict:
    """Construye el artefacto inicial a partir de las referencias del banco HU-02."""
    if filas is None:
        filas = dataset.read_dataset()
    return {
        "version": VERSION,
        "prompt": prompt_actual(),
        "modelo": modelo or llm.planner_model(),
        "origen": "referencia-banco",
        "respuestas": [
            {
                "id": fila["id"],
                "clave": clave_de(fila),
                "prompt_version": prompt_actual()["etiqueta"],
                "contenido": json.dumps(
                    programa_referencia(fila), ensure_ascii=False, sort_keys=True
                ),
            }
            for fila in filas
        ],
    }


def grabar(
    filas: list[dict],
    *,
    ruta: Path = DEFAULT_PATH,
    proveedor_real: Callable[..., dict] | None = None,
    url: str | None = None,
    timeout: float = pipeline.TIEMPO_ESPERA_LLM,
) -> dict:
    """Graba respuestas del proveedor real usando la misma ruta de caché de HU-25.

    Sin `proveedor_real` exige API key cuando el endpoint es DeepSeek: grabar es
    una operación pagada y explícita, nunca un efecto colateral del replay.
    """
    url = url or llm.base_url("planner")
    if proveedor_real is None and "api.deepseek.com" in url:
        clave = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        if not clave:
            raise ErrorReplay(
                "Para grabar respuestas del proveedor falta DEEPSEEK_API_KEY (o LLM_API_KEY)."
            )
    proveedor_real = proveedor_real or llm.chat
    prompt = prompt_actual()
    respuestas = []
    for fila in filas:
        cuerpo = pipeline.cuerpo_planificador(fila["solicitud"])
        respuesta = llm_resiliente.consultar(
            cuerpo,
            url=url,
            timeout=timeout,
            proveedor=proveedor_real,
            validador=pipeline._programa_de,
        )
        contenido = respuesta["choices"][0]["message"]["content"]
        respuestas.append(
            {
                "id": fila["id"],
                # La clave se calcula con la URL canónica del replay, no con la del
                # proveedor: así el mismo artefacto sirve en el host y en CI.
                "clave": clave_de(fila),
                "prompt_version": prompt["etiqueta"],
                "contenido": contenido,
            }
        )
    datos = {
        "version": VERSION,
        "prompt": prompt,
        "modelo": llm.planner_model(),
        "origen": "proveedor",
        "respuestas": respuestas,
    }
    escribir(datos, ruta)
    return datos


def escribir(datos: dict, ruta: Path = DEFAULT_PATH) -> Path:
    """Escribe el artefacto con orden estable para que el diff sea revisable."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ruta
