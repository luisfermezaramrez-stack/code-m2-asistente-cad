"""Comparación del banco contra un baseline versionado (HU-46, SPEC-047).

El módulo es puro: lee un resumen JSON y su CSV por caso, valida el baseline
versionado y devuelve un resultado serializable. Quien decide escribir archivos
o terminar con código de error es la CLI `scripts/verificar_alertas.py`.

Las métricas son acierto, declinaciones correctas y errores silenciosos (HU-07).
Los umbrales viven en el artefacto `data/alertas_baseline.json`, no aquí (RNF-3).
"""

from __future__ import annotations

import csv
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from m2_cad import declinacion

VERSION = 1
BASELINE_PATH = Path("data/alertas_baseline.json")
SALIDA_DIR = Path("outputs/alertas")
UMBRALES_POR_DEFECTO = {
    "acierto": 0.0,
    "declinaciones_correctas": 0,
    "errores_silenciosos": 0,
}
METRICAS = tuple(UMBRALES_POR_DEFECTO)
CAMPOS_CSV = ("id", "familia", "esperado", "estado", "correcto", "causa")
TOLERANCIA = 1e-9


class ErrorAlertas(ValueError):
    """El baseline o la corrida no cumplen el esquema acordado."""


def ahora() -> str:
    """Marca de tiempo UTC, legible y estable para artefactos y trazabilidad."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _leer_json(ruta: Path, nombre: str) -> dict[str, Any]:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ErrorAlertas(f"no existe el {nombre}: {ruta}") from exc
    except json.JSONDecodeError as exc:
        raise ErrorAlertas(f"{nombre} no es JSON válido: {ruta}") from exc
    if not isinstance(datos, dict):
        raise ErrorAlertas(f"el {nombre} debe ser un objeto JSON: {ruta}")
    return datos


def _numero(valor: object, nombre: str) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErrorAlertas(f"{nombre} debe ser numérico, no {type(valor).__name__}")
    return float(valor)


def _texto(valor: object, nombre: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorAlertas(f"{nombre} debe ser texto no vacío")
    return valor.strip()


def _booleano(valor: object, nombre: str) -> bool:
    if isinstance(valor, bool):
        return valor
    texto = str(valor).strip().lower()
    if texto in {"true", "1", "sí", "si"}:
        return True
    if texto in {"false", "0", "no"}:
        return False
    raise ErrorAlertas(f"{nombre} no es booleano: {valor!r}")


def metricas_por_caso(registros: list[dict[str, Any]]) -> dict[str, Any]:
    """Deriva las tres métricas comparables del CSV por caso (HU-07, RF-2).

    Un error silencioso es una pieza construida y aceptada que no cumple la
    referencia: positivo con geometría fuera de tolerancia o negativo construido.
    """
    if not registros:
        raise ErrorAlertas("la corrida no tiene casos")
    correctos = sum(bool(registro["correcto"]) for registro in registros)
    declinaciones = sum(
        bool(registro["correcto"]) and registro["esperado"] == "declinar" for registro in registros
    )
    silenciosos = sum(
        not registro["correcto"] and registro["estado"] == "construida" for registro in registros
    )
    return {
        "acierto": correctos / len(registros),
        "declinaciones_correctas": declinaciones,
        "errores_silenciosos": silenciosos,
    }


def _casos_de_registros(registros: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    casos: dict[str, dict[str, Any]] = {}
    for registro in registros:
        identificador = _texto(registro.get("id"), "id del caso")
        if identificador in casos:
            raise ErrorAlertas(f"caso duplicado en la corrida: {identificador}")
        try:
            causa = declinacion.normalizar(registro.get("causa"))
        except ValueError as exc:
            raise ErrorAlertas(str(exc)) from exc
        casos[identificador] = {
            "familia": _texto(registro.get("familia"), "familia del caso"),
            "esperado": _texto(registro.get("esperado"), "esperado del caso"),
            "correcto": _booleano(registro.get("correcto"), "correcto del caso"),
            "estado": _texto(registro.get("estado"), "estado del caso"),
            "causa": causa,
        }
    return casos


def leer_corrida(resumen: Path, csv_casos: Path) -> dict[str, Any]:
    """Lee el JSON de resumen y el CSV por caso, y valida su coherencia."""
    datos = _leer_json(resumen, "resumen de la corrida")
    try:
        with csv_casos.open(encoding="utf-8", newline="") as archivo:
            lector = csv.DictReader(archivo)
            cabecera = lector.fieldnames or []
            ausentes = [campo for campo in CAMPOS_CSV if campo not in cabecera]
            if ausentes:
                raise ErrorAlertas(f"el CSV no incluye: {', '.join(ausentes)}")
            registros = list(lector)
    except FileNotFoundError as exc:
        raise ErrorAlertas(f"no existe el CSV de casos: {csv_casos}") from exc

    casos = _casos_de_registros(registros)
    metricas = metricas_por_caso(list(casos.values()))
    acierto_resumen = _numero(datos.get("acierto"), "acierto del resumen")
    if len(casos) != int(datos.get("casos", -1)):
        raise ErrorAlertas("el resumen y el CSV no cubren el mismo número de casos")
    if abs(acierto_resumen - metricas["acierto"]) > 1e-6:
        raise ErrorAlertas("el acierto del resumen no coincide con el CSV por caso")
    return {
        "origen": str(resumen),
        "modo": datos.get("modo", "real"),
        "modelo": datos.get("modelo", ""),
        "prompt_version": datos.get("prompt_version", ""),
        "metrica": metricas,
        "casos": casos,
    }


def validar_baseline(datos: dict[str, Any]) -> dict[str, Any]:
    """Valida el esquema v1 del baseline antes de usarlo como referencia."""
    if datos.get("version") != VERSION:
        raise ErrorAlertas(f"el baseline debe tener version={VERSION}")
    _texto(datos.get("id"), "id del baseline")
    metricas = datos.get("metrica") or {}
    for nombre in METRICAS:
        if nombre not in metricas:
            raise ErrorAlertas(f"falta la métrica {nombre} en el baseline")
        _numero(metricas[nombre], f"metrica.{nombre}")
    umbrales = datos.get("umbrales") or {}
    for nombre in METRICAS:
        if nombre not in umbrales:
            raise ErrorAlertas(f"falta el umbral {nombre} en el baseline")
        valor = _numero(umbrales[nombre], f"umbrales.{nombre}")
        if valor < 0:
            raise ErrorAlertas(f"el umbral {nombre} no puede ser negativo")
    casos = datos.get("casos") or {}
    if not isinstance(casos, dict) or not casos:
        raise ErrorAlertas("el baseline no tiene casos")
    for identificador, caso in casos.items():
        if not isinstance(caso, dict):
            raise ErrorAlertas(f"el caso {identificador} del baseline es inválido")
        _texto(caso.get("familia"), f"familia de {identificador}")
        _texto(caso.get("estado"), f"estado de {identificador}")
        try:
            declinacion.normalizar(caso.get("causa"))
        except ValueError as exc:
            raise ErrorAlertas(str(exc)) from exc
        _booleano(caso.get("correcto"), f"correcto de {identificador}")
    actualizado = datos.get("actualizado") or {}
    for campo in ("por", "fecha", "corrida", "motivo"):
        _texto(actualizado.get(campo), f"actualizado.{campo}")
    if not isinstance(datos.get("historial", []), list):
        raise ErrorAlertas("el historial del baseline debe ser una lista")
    return datos


def cargar_baseline(ruta: Path = BASELINE_PATH) -> dict[str, Any]:
    """Carga y valida el baseline versionado desde disco."""
    return validar_baseline(_leer_json(ruta, "baseline"))


def construir_baseline(
    corrida: dict[str, Any],
    *,
    autor: str,
    motivo: str,
    corrida_origen: str,
    issue: str = "",
    anterior: dict[str, Any] | None = None,
    fecha: str | None = None,
) -> dict[str, Any]:
    """Construye un baseline nuevo con trazabilidad obligatoria (RF-5, AC4)."""
    marca = fecha or ahora()
    actualizado = {
        "por": _texto(autor, "autor"),
        "fecha": marca,
        "corrida": _texto(corrida_origen, "corrida de origen"),
        "motivo": _texto(motivo, "motivo"),
    }
    if issue:
        actualizado["issue"] = _texto(issue, "issue")
    historial = list((anterior or {}).get("historial", []))
    historial.append(actualizado)
    identidad = re.sub(r"[^A-Za-z0-9._-]+", "-", corrida_origen).strip("-")[:48]
    return validar_baseline(
        {
            "version": VERSION,
            "id": f"baseline-{identidad or 'corrida'}-{marca}",
            "fuente": corrida["modo"],
            "modelo": corrida["modelo"],
            "prompt_version": corrida["prompt_version"],
            "metrica": corrida["metrica"],
            "casos": corrida["casos"],
            "umbrales": (anterior or {}).get("umbrales", UMBRALES_POR_DEFECTO),
            "actualizado": actualizado,
            "historial": historial,
        }
    )


def comparar(
    baseline: dict[str, Any], corrida: dict[str, Any], *, fecha: str | None = None
) -> dict[str, Any]:
    """Compara la corrida contra el baseline y devuelve un resultado serializable."""
    validar_baseline(baseline)
    ids_base = set(baseline["casos"])
    ids_corrida = set(corrida["casos"])
    if ids_base != ids_corrida:
        faltan = sorted(ids_base - ids_corrida)
        sobran = sorted(ids_corrida - ids_base)
        raise ErrorAlertas(
            f"los casos no coinciden; faltan {faltan or 'ninguno'} y sobran {sobran or 'ninguno'}"
        )

    umbrales = baseline["umbrales"]
    sentido = {"acierto": -1, "declinaciones_correctas": -1, "errores_silenciosos": 1}
    metricas: dict[str, dict[str, Any]] = {}
    for nombre in METRICAS:
        referencia = _numero(baseline["metrica"][nombre], nombre)
        obtenido = _numero(corrida["metrica"][nombre], nombre)
        delta = (obtenido - referencia) * sentido[nombre]
        umbral = _numero(umbrales[nombre], f"umbral {nombre}")
        metricas[nombre] = {
            "baseline": referencia,
            "corrida": obtenido,
            "delta": round(delta, 6) or 0.0,
            "umbral": umbral,
            "degradada": delta > umbral + TOLERANCIA,
        }

    cambiados = []
    campos = ("correcto", "estado", "causa")
    for identificador in sorted(ids_base):
        antes = baseline["casos"][identificador]
        despues = corrida["casos"][identificador]
        diferencias = [campo for campo in campos if antes[campo] != despues[campo]]
        if not diferencias:
            continue
        cambiados.append(
            {
                "id": identificador,
                "familia": despues["familia"],
                "cambios": diferencias,
                "antes": {campo: antes[campo] for campo in campos},
                "despues": {campo: despues[campo] for campo in campos},
            }
        )

    degradadas = [nombre for nombre, datos in metricas.items() if datos["degradada"]]
    return {
        "version": VERSION,
        "fecha": fecha or ahora(),
        "baseline": baseline["id"],
        "corrida": corrida["origen"],
        "modo": corrida["modo"],
        "regresion": bool(degradadas),
        "codigo": 1 if degradadas else 0,
        "metrica": metricas,
        "degradadas": degradadas,
        "casos_cambiados": cambiados,
        "umbrales": umbrales,
    }


def markdown(resultado: dict[str, Any]) -> str:
    """Resumen legible de la alerta, con familia y causa de cada caso afectado."""
    estado = "SÍ" if resultado["regresion"] else "NO"
    lineas = [
        "# Alerta de regresión de calidad · HU-46",
        "",
        f"- **Fecha**: {resultado['fecha']}",
        f"- **Baseline**: `{resultado['baseline']}`",
        f"- **Corrida**: `{resultado['corrida']}` ({resultado['modo']})",
        f"- **Regresión**: **{estado}**",
        "",
        "## Métricas",
        "",
        "| Métrica | Baseline | Corrida | Degradación | Umbral | Estado |",
        "|---|---:|---:|---:|---:|---|",
    ]
    nombres = {
        "acierto": "acierto",
        "declinaciones_correctas": "declinaciones correctas",
        "errores_silenciosos": "errores silenciosos",
    }
    for nombre, datos in resultado["metrica"].items():
        estado_metrica = "DEGRADADA" if datos["degradada"] else "ok"
        lineas.append(
            f"| {nombres[nombre]} | {datos['baseline']} | {datos['corrida']} | "
            f"{datos['delta']} | {datos['umbral']} | {estado_metrica} |"
        )
    lineas += ["", "## Casos cambiados", ""]
    if resultado["casos_cambiados"]:
        lineas += [
            "| Caso | Familia | Cambios | Antes | Después | Causa (antes → después) |",
            "|---|---|---|---|---|---|",
        ]
        for caso in resultado["casos_cambiados"]:
            antes = ", ".join(f"{k}={v}" for k, v in caso["antes"].items())
            despues = ", ".join(f"{k}={v}" for k, v in caso["despues"].items())
            causa = f"{caso['antes']['causa']} → {caso['despues']['causa']}"
            lineas.append(
                f"| {caso['id']} | {caso['familia']} | {', '.join(caso['cambios'])} | "
                f"{antes} | {despues} | {causa} |"
            )
    else:
        lineas.append("Ningún caso cambió de resultado.")
    return "\n".join(lineas) + "\n"


def escribir(resultado: dict[str, Any], directorio: Path = SALIDA_DIR) -> dict[str, str]:
    """Escribe el JSON de auditoría y, sólo si hay regresión, el Markdown de alerta."""
    directorio.mkdir(parents=True, exist_ok=True)
    marca = resultado["fecha"]
    ruta_json = directorio / f"alerta-{marca}.json"
    contenido = json.dumps(resultado, indent=2, ensure_ascii=False)
    ruta_json.write_text(contenido, encoding="utf-8")
    (directorio / "ultimo.json").write_text(contenido, encoding="utf-8")
    rutas = {"json": str(ruta_json), "ultimo_json": str(directorio / "ultimo.json")}
    ruta_md = directorio / f"alerta-{marca}.md"
    ultimo_md = directorio / "ultimo.md"
    if resultado["regresion"]:
        texto = markdown(resultado)
        ruta_md.write_text(texto, encoding="utf-8")
        ultimo_md.write_text(texto, encoding="utf-8")
        rutas.update(markdown=str(ruta_md), ultimo_markdown=str(ultimo_md))
    else:
        ruta_md.unlink(missing_ok=True)
        ultimo_md.unlink(missing_ok=True)
    return rutas
