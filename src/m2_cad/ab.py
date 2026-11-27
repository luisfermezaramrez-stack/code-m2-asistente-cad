"""Comparación A/B de prompts y modelos sobre el mismo banco (HU-52 / SPEC-053).

Una variante es prompt versionado (SPEC-034) + modelo servido (con su versión). La
comparación corrige el banco con la misma temperatura y registra dos corridas en
MLflow; el reporte compara por familia y lista los casos que cambiaron de resultado.
Promover una variante es siempre una decisión explícita: aquí no se decide nada.

El modo real gasta tokens y no corre en CI. El modo replay consume respuestas
grabadas por variante (SPEC-045), sin red, API key ni tokens.
"""

from __future__ import annotations

import csv
import json
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from m2_cad import banco, banco_replay, pipeline, prompts, seguimiento

VERSION = 1
EXPERIMENTO_AB = "m2-cad-ab"
SALIDA_DIR = Path("outputs/ab")
CAMPOS_CAMBIO = ("estado", "correcto", "detalle")
METRICAS_TABLA = (
    "casos",
    "piezas_conformes",
    "declinaciones_correctas",
    "errores_silenciosos",
    "acierto",
    "latencia_media_s",
    "tokens_entrada",
    "tokens_salida",
    "costo_usd",
)


class ErrorAB(ValueError):
    """La configuración de la comparación o sus artefactos no son válidos."""


@dataclass(frozen=True)
class Variante:
    """Prompt exacto y modelo exacto que se van a comparar."""

    etiqueta: str
    prompt: prompts.Prompt
    modelo: str
    version_modelo: str
    replay: Path | None = None


def identidad_prompt(prompt: prompts.Prompt) -> dict[str, Any]:
    """Identidad del prompt que viaja a MLflow y al artefacto de replay."""
    return {
        "id": prompt.id,
        "version": prompt.version,
        "sha256": prompt.sha256,
        "etiqueta": prompt.etiqueta,
    }


def construir_variante(
    etiqueta: str,
    selector_prompt: str,
    modelo: str = "",
    *,
    raiz: Path | None = None,
    replay: Path | None = None,
    version_modelo: str = "",
) -> Variante:
    """Resuelve `planner-vN` a un prompt registrado y fija su modelo (AC3)."""
    nombre = etiqueta.strip()
    if not nombre:
        raise ErrorAB("La etiqueta de la variante no puede estar vacía.")
    selector = selector_prompt.strip()
    id_prompt, separador, texto_version = selector.rpartition("-v")
    if not separador or not id_prompt:
        raise ErrorAB(f"El prompt «{selector}» debe tener forma <id>-v<número>.")
    try:
        version = int(texto_version)
    except ValueError as exc:
        raise ErrorAB(f"La versión de «{selector}» no es un entero.") from exc
    prompt = prompts.cargar_version(id_prompt, version, raiz=raiz)
    modelo_resuelto = modelo.strip() or pipeline.llm.planner_model()
    return Variante(
        etiqueta=nombre,
        prompt=prompt,
        modelo=modelo_resuelto,
        version_modelo=(
            version_modelo.strip() or os.environ.get("LLM_MODEL_VERSION") or modelo_resuelto
        ),
        replay=Path(replay) if replay else None,
    )


def validar_variantes(a: Variante, b: Variante, filas: list[dict]) -> dict[str, Any]:
    """Exige dos variantes distintas sobre el mismo banco y temperatura (RNF-2)."""
    if a.etiqueta == b.etiqueta:
        raise ErrorAB("Las variantes A y B deben tener etiquetas distintas.")
    if (a.prompt.etiqueta, a.modelo) == (b.prompt.etiqueta, b.modelo):
        raise ErrorAB("Las variantes son idénticas: cambia el prompt o el modelo.")
    if not filas:
        raise ErrorAB("El banco no tiene casos.")
    if bool(a.replay) != bool(b.replay):
        raise ErrorAB("En replay las dos variantes necesitan su artefacto de respuestas.")
    return {
        "casos": len(filas),
        "temperatura": pipeline.TEMPERATURA_LLM,
        "prompt_vigente": prompts.cargar().etiqueta,
        "modo": "replay" if a.replay else "real",
    }


@contextmanager
def _variante_activa(variante: Variante) -> Iterator[None]:
    """Fija prompt, modelo, proveedor y URL mientras corre una variante; restaura después."""
    originales = (
        pipeline.PROMPT_SISTEMA,
        pipeline.llm.planner_model,
        pipeline.llm.base_url,
        pipeline.llm.chat,
    )
    pipeline.PROMPT_SISTEMA = variante.prompt.texto
    pipeline.llm.planner_model = lambda: variante.modelo
    try:
        yield
    finally:
        (
            pipeline.PROMPT_SISTEMA,
            pipeline.llm.planner_model,
            pipeline.llm.base_url,
            pipeline.llm.chat,
        ) = originales


def ejecutar_variante(
    variante: Variante,
    filas: list[dict],
    *,
    id_comparacion: str,
    salida: Path,
    precio_entrada: float = 0.0,
    precio_salida: float = 0.0,
    configuracion: seguimiento.Configuracion | None = None,
) -> dict[str, Any]:
    """Corre el banco con una variante, registra MLflow y guarda su CSV/JSON."""
    config = configuracion or seguimiento.Configuracion.desde_entorno()
    identidad = identidad_prompt(variante.prompt)
    corrida = seguimiento.iniciar_corrida(
        EXPERIMENTO_AB,
        nombre=f"{id_comparacion}-{variante.etiqueta}",
        tags={
            "comparacion_id": id_comparacion,
            "variante": variante.etiqueta,
            "prompt_version": identidad["etiqueta"],
            "prompt_sha256": identidad["sha256"],
            "modelo": variante.modelo,
            "version_modelo": variante.version_modelo,
        },
        configuracion=config,
    )
    corrida.registrar_params(
        comparacion_id=id_comparacion,
        variante=variante.etiqueta,
        prompt=identidad["etiqueta"],
        prompt_sha256=identidad["sha256"],
        modelo=variante.modelo,
        version_modelo=variante.version_modelo,
        temperatura=pipeline.TEMPERATURA_LLM,
        n_casos=len(filas),
        precio_entrada=precio_entrada,
        precio_salida=precio_salida,
        modo="replay" if variante.replay else "real",
    )

    registros: list[dict] = []
    with _variante_activa(variante):
        preparado = None
        if variante.replay is not None:
            try:
                preparado = banco_replay.preparar(
                    filas,
                    variante.replay,
                    prompt_esperado=identidad,
                    modelo_esperado=variante.modelo,
                )
            except banco_replay.ErrorReplay as exc:
                corrida.finalizar(estado="error", error="ErrorReplay")
                raise ErrorAB(str(exc)) from exc
            pipeline.llm.base_url = lambda role=None: banco_replay.URL_REPLAY
            proveedor = banco_replay.proveedor(preparado)
        else:
            proveedor = pipeline.llm.chat
        contador = banco.ContadorUso(proveedor)
        pipeline.llm.chat = contador
        try:
            with tempfile.TemporaryDirectory() as temporal:
                for fila in filas:
                    antes = (contador.entrada, contador.salida)
                    registro = banco.evaluar_caso(fila, directorio=Path(temporal))
                    registro["tokens_entrada"] = contador.entrada - antes[0]
                    registro["tokens_salida"] = contador.salida - antes[1]
                    registros.append(registro)
        except pipeline.ModeloNoDisponible as exc:
            corrida.finalizar(estado="error", error="ModeloNoDisponible")
            raise ErrorAB(str(exc)) from exc

    resumen = banco.resumir(registros, precio_entrada=precio_entrada, precio_salida=precio_salida)
    resumen.update(
        comparacion_id=id_comparacion,
        variante=variante.etiqueta,
        prompt_version=identidad["etiqueta"],
        prompt_sha256=identidad["sha256"],
        modelo=variante.modelo,
        version_modelo=variante.version_modelo,
        temperatura=pipeline.TEMPERATURA_LLM,
        modo="replay" if variante.replay else "real",
    )
    corrida.registrar_metricas(
        acierto=resumen["acierto"],
        latencia_media_s=resumen["latencia_media_s"],
        tokens_entrada=resumen["tokens_entrada"],
        tokens_salida=resumen["tokens_salida"],
        costo_usd=resumen["costo_usd"],
    )
    corrida.finalizar(estado="completado")

    salida.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base = salida / f"{re.sub(r'[^A-Za-z0-9._-]+', '_', variante.etiqueta)}-{marca}"
    with base.with_suffix(".csv").open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=banco.CAMPOS)
        escritor.writeheader()
        escritor.writerows(
            {campo: registro[campo] for campo in banco.CAMPOS} for registro in registros
        )
    base.with_suffix(".json").write_text(
        json.dumps({"resumen": resumen, "casos": registros}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "variante": variante.etiqueta,
        "prompt": identidad,
        "modelo": variante.modelo,
        "version_modelo": variante.version_modelo,
        "modo": resumen["modo"],
        "precio_entrada": precio_entrada,
        "precio_salida": precio_salida,
        "resumen": resumen,
        "casos": registros,
    }


def _metricas(
    registros: list[dict], *, precio_entrada: float = 0.0, precio_salida: float = 0.0
) -> dict[str, Any]:
    """Métricas compartidas y derivadas de los casos del banco (RF-3)."""
    resumen = banco.resumir(registros, precio_entrada=precio_entrada, precio_salida=precio_salida)
    resumen.update(
        casos=len(registros),
        piezas_conformes=sum(
            bool(registro["correcto"]) and registro["esperado"] != "declinar"
            for registro in registros
        ),
        declinaciones_correctas=sum(
            bool(registro["correcto"]) and registro["esperado"] == "declinar"
            for registro in registros
        ),
        errores_silenciosos=sum(
            not registro["correcto"] and registro["estado"] == "construida"
            for registro in registros
        ),
    )
    return resumen


def comparar(
    resultados: list[dict[str, Any]],
    *,
    id_comparacion: str,
    contexto: dict[str, Any],
) -> dict[str, Any]:
    """Compara dos resultados del mismo banco: por familia, totales y casos cambiados."""
    if len(resultados) != 2:
        raise ErrorAB("La comparación necesita exactamente dos variantes.")
    a, b = resultados
    if a["variante"] == b["variante"]:
        raise ErrorAB("Las variantes comparadas deben tener etiquetas distintas.")

    por_id = [
        {registro["id"]: registro for registro in resultado["casos"]} for resultado in resultados
    ]
    if set(por_id[0]) != set(por_id[1]):
        raise ErrorAB("Las variantes no corrieron sobre el mismo banco (los IDs difieren).")

    por_familia: dict[str, dict[str, dict[str, Any]]] = {}
    familias = sorted({registro["familia"] for registro in resultados[0]["casos"]})
    for familia in familias:
        por_familia[familia] = {}
        for resultado in resultados:
            registros = [
                registro for registro in resultado["casos"] if registro["familia"] == familia
            ]
            por_familia[familia][resultado["variante"]] = _metricas(
                registros,
                precio_entrada=resultado["precio_entrada"],
                precio_salida=resultado["precio_salida"],
            )

    totales = {
        resultado["variante"]: _metricas(
            resultado["casos"],
            precio_entrada=resultado["precio_entrada"],
            precio_salida=resultado["precio_salida"],
        )
        for resultado in resultados
    }

    cambiados = []
    for caso_id in sorted(por_id[0]):
        antes, despues = por_id[0][caso_id], por_id[1][caso_id]
        cambios = [campo for campo in CAMPOS_CAMBIO if antes.get(campo) != despues.get(campo)]
        if cambios:
            cambiados.append(
                {
                    "id": caso_id,
                    "familia": despues["familia"],
                    "cambios": cambios,
                    "antes": {campo: antes.get(campo) for campo in cambios},
                    "despues": {campo: despues.get(campo) for campo in cambios},
                }
            )

    return {
        "version": VERSION,
        "id": id_comparacion,
        "fecha": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "contexto": contexto,
        "variantes": [
            {
                "etiqueta": resultado["variante"],
                "prompt": resultado["prompt"],
                "modelo": resultado["modelo"],
                "version_modelo": resultado["version_modelo"],
                "modo": resultado["modo"],
            }
            for resultado in resultados
        ],
        "por_familia": por_familia,
        "totales": totales,
        "casos_cambiados": cambiados,
        "promocion": "decisión explícita; este reporte no selecciona ganador",
    }


def _valor(valor: Any) -> str:
    return f"{valor:.6f}" if isinstance(valor, float) else str(valor)


def markdown(resultado: dict[str, Any]) -> str:
    """Reporte legible con trazabilidad, métricas por familia y casos cambiados."""
    variantes = resultado["variantes"]
    etiquetas = [variante["etiqueta"] for variante in variantes]
    a, b = etiquetas
    contexto = resultado["contexto"]
    lineas = [
        "# Comparación A/B de prompts y modelos · HU-52",
        "",
        f"- **ID**: `{resultado['id']}`",
        f"- **Fecha**: {resultado['fecha']}",
        f"- **Casos**: {contexto['casos']} · **Temperatura**: {contexto['temperatura']}",
        f"- **Modo**: {contexto['modo']} · **Prompt vigente**: {contexto['prompt_vigente']}",
        f"- **Promoción**: {resultado['promocion']}",
        "",
        "## Variantes",
        "",
        "| Variante | Prompt | sha256 | Modelo | Versión de modelo |",
        "|---|---|---|---|---|",
    ]
    for variante in variantes:
        prompt = variante["prompt"]
        lineas.append(
            f"| {variante['etiqueta']} | {prompt['etiqueta']} | `{prompt['sha256']}` | "
            f"{variante['modelo']} | {variante['version_modelo']} |"
        )

    lineas += [
        "",
        "## Totales",
        "",
        "| Métrica | " + a + " | " + b + " | Δ (B−A) |",
        "|---|---:|---:|---:|",
    ]
    for metrica in METRICAS_TABLA:
        izquierda = resultado["totales"][a][metrica]
        derecha = resultado["totales"][b][metrica]
        delta = f"{float(derecha) - float(izquierda):+.6f}"
        lineas.append(f"| {metrica} | {_valor(izquierda)} | {_valor(derecha)} | {delta} |")

    for familia, datos in resultado["por_familia"].items():
        lineas += [
            "",
            f"## Familia: {familia}",
            "",
            "| Métrica | " + a + " | " + b + " | Δ (B−A) |",
            "|---|---:|---:|---:|",
        ]
        for metrica in METRICAS_TABLA:
            izquierda = datos[a][metrica]
            derecha = datos[b][metrica]
            delta = f"{float(derecha) - float(izquierda):+.6f}"
            lineas.append(f"| {metrica} | {_valor(izquierda)} | {_valor(derecha)} | {delta} |")

    lineas += ["", "## Casos que cambiaron de resultado", ""]
    if resultado["casos_cambiados"]:
        lineas += ["| Caso | Familia | Cambios | " + a + " | " + b + " |", "|---|---|---|---|---|"]
        for caso in resultado["casos_cambiados"]:
            antes = ", ".join(f"{campo}={valor}" for campo, valor in caso["antes"].items())
            despues = ", ".join(f"{campo}={valor}" for campo, valor in caso["despues"].items())
            lineas.append(
                f"| {caso['id']} | {caso['familia']} | {', '.join(caso['cambios'])} | "
                f"{antes} | {despues} |"
            )
    else:
        lineas.append("Ningún caso cambió de resultado entre las dos variantes.")
    return "\n".join(lineas) + "\n"


def escribir(resultado: dict[str, Any], directorio: Path = SALIDA_DIR) -> dict[str, str]:
    """Escribe el JSON de auditoría y el Markdown del reporte."""
    directorio.mkdir(parents=True, exist_ok=True)
    marca = resultado["fecha"]
    contenido = json.dumps(resultado, indent=2, ensure_ascii=False)
    ruta_json = directorio / f"ab-{marca}.json"
    ruta_md = directorio / f"ab-{marca}.md"
    ruta_json.write_text(contenido, encoding="utf-8")
    ruta_md.write_text(markdown(resultado), encoding="utf-8")
    (directorio / "ultimo.json").write_text(contenido, encoding="utf-8")
    (directorio / "ultimo.md").write_text(markdown(resultado), encoding="utf-8")
    return {
        "json": str(ruta_json),
        "markdown": str(ruta_md),
        "ultimo_json": str(directorio / "ultimo.json"),
        "ultimo_markdown": str(directorio / "ultimo.md"),
    }
