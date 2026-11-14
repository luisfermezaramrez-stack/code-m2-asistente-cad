"""HU-07: evaluación HTTP del banco; las referencias nunca se envían al pipeline.

SPEC-016 (specs/016-hu-07-corrida-banco/spec.md), AC1–AC5: comando único,
reporte por familia, trazabilidad, causas de fallo y publicación de evidencia.
"""

import argparse
import hashlib
import json
import math
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx

from m2_cad.dataset import DEFAULT_PATH, json_object, read_dataset, validate_dataset

CONFORME = "conforme"
NO_CONFORME = "geometria_no_conforme"
DECLINACION = "declinacion_explicita"
INDEBIDA = "declinacion_indebida"
TECNICO = "fallo_tecnico"
CATEGORIAS = (CONFORME, NO_CONFORME, DECLINACION, INDEBIDA, TECNICO)
TOLERANCIA = 0.02


def _numero(valor):
    if isinstance(valor, bool):
        raise ValueError("Una medida no puede ser booleana")
    numero = float(valor)
    if not math.isfinite(numero) or numero <= 0:
        raise ValueError("Medida no positiva o no finita")
    return numero


def clasificar(caso, respuesta):
    """Clasifica sin confundir fallos HTTP con una negativa explícita del modelo."""
    negativo = caso["resultado_esperado"] == "declinar"
    try:
        cuerpo = respuesta.json()
    except ValueError:
        return TECNICO, "Respuesta sin JSON válido", {}, False
    if not isinstance(cuerpo, dict):
        return TECNICO, "Respuesta JSON no es un objeto", {}, False

    motivo = cuerpo.get("detail")
    explicita = (
        respuesta.status_code == 422
        and respuesta.headers.get("X-Resultado-Tipo") == DECLINACION
        and isinstance(motivo, str)
        and motivo.startswith("Pieza declinada:")
        and bool(motivo.removeprefix("Pieza declinada:").strip())
    )
    if explicita:
        return DECLINACION if negativo else INDEBIDA, motivo, {}, False
    if respuesta.status_code != 200:
        return TECNICO, f"HTTP {respuesta.status_code}: {motivo}", {}, False

    try:
        if not isinstance(cuerpo.get("step"), str) or not cuerpo["step"].strip():
            raise ValueError("Falta STEP en la respuesta")
        volumen = _numero(cuerpo["volumen_mm3"])
        caja = cuerpo["caja_mm"]
        caja = caja.split("x") if isinstance(caja, str) else caja
        if not isinstance(caja, (tuple, list)) or len(caja) != 3:
            raise ValueError("La caja debe tener exactamente tres ejes X/Y/Z")
        valores = [volumen, *(_numero(lado) for lado in caja)]
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        return TECNICO, f"Respuesta de construcción incompleta: {exc}", {}, False

    medido = dict(zip(("volumen_mm3", "x_mm", "y_mm", "z_mm"), valores, strict=True))
    if negativo:
        return NO_CONFORME, "Se construyó una solicitud fuera del alcance", medido, True
    esperado = json_object(caso["resultado_esperado"])
    referencias = [esperado["volumen_mm3"], *esperado["caja_xyz_mm"]]
    errores = {
        nombre: (actual - referencia) / referencia
        for (nombre, actual), referencia in zip(medido.items(), referencias, strict=True)
    }
    medido["desviacion_relativa"] = errores
    fuera = [nombre for nombre, error in errores.items() if abs(error) > TOLERANCIA + 1e-12]
    if fuera:
        return NO_CONFORME, "Fuera de ±2 %: " + ", ".join(fuera), medido, True
    return CONFORME, "Volumen y cada eje X/Y/Z dentro de ±2 %", medido, False


def evaluar_caso(cliente, caso):
    identificador = uuid.uuid4().hex
    inicio = time.perf_counter()
    resultado = {
        "id": caso["id"],
        "familia": caso["familia"],
        "positivo": caso["resultado_esperado"] != "declinar",
        "request_id": identificador,
        "registro_url": str(cliente.base_url).rstrip("/") + f"/registros/{identificador}",
        "registro_confirmado": False,
        "step": "no disponible",
        "error_silencioso": False,
        "medido": {},
    }
    try:
        # El único dato de entrada al modelo es el texto; ID solo en cabecera HTTP.
        respuesta = cliente.post(
            "/generar",
            json={"texto": caso["solicitud"]},
            headers={"X-Request-ID": identificador, "Accept": "application/json"},
        )
        categoria, causa, medido, silencioso = clasificar(caso, respuesta)
        resultado.update(
            categoria=categoria,
            causa=causa,
            medido=medido,
            error_silencioso=silencioso,
            http_status=respuesta.status_code,
        )
        if categoria in (DECLINACION, INDEBIDA):
            resultado["step"] = "no aplica"
        elif medido:
            resultado["step"] = resultado["registro_url"] + "/step"
        resultado["correlacion_respuesta"] = respuesta.headers.get("X-Registro-ID") == identificador
    except httpx.HTTPError as exc:
        resultado.update(categoria=TECNICO, causa=type(exc).__name__, http_status=None)
    resultado["latencia_ms"] = (time.perf_counter() - inicio) * 1000

    # Un timeout puede ocurrir después de registrar: conserva el ID y busca evidencia.
    try:
        registro = cliente.get(f"/registros/{identificador}")
        fila = registro.json()
        if (
            registro.status_code == 200
            and isinstance(fila, dict)
            and fila.get("id") == identificador
        ):
            resultado["registro_confirmado"] = True
            resultado["registro"] = fila
    except (httpx.HTTPError, ValueError):
        pass
    return resultado


def resumir(resultados):
    familias = {}
    for familia in sorted({fila["familia"] for fila in resultados}):
        filas = [fila for fila in resultados if fila["familia"] == familia]
        conteo = Counter(fila["categoria"] for fila in filas)
        familias[familia] = {
            "positivos": sum(fila["positivo"] for fila in filas),
            "negativos": sum(not fila["positivo"] for fila in filas),
            **{categoria: conteo[categoria] for categoria in CATEGORIAS},
            "errores_silenciosos": sum(fila["error_silencioso"] for fila in filas),
        }
    conformes = sum(fila["categoria"] == CONFORME for fila in resultados)
    declinaciones = sum(fila["categoria"] == DECLINACION for fila in resultados)
    return {
        "conformes": conformes,
        "positivos": 30,
        "meta_conformes": 26,
        "declinaciones_correctas": declinaciones,
        "negativos": 10,
        "meta_declinaciones": 8,
        "cumple_metas": conformes >= 26 and declinaciones >= 8,
        "errores_silenciosos": sum(fila["error_silencioso"] for fila in resultados),
        "registros_confirmados": sum(fila["registro_confirmado"] for fila in resultados),
        "por_familia": familias,
    }


def _celda(valor):
    return str(valor).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def guardar_reporte(reporte, directorio):
    directorio.mkdir(parents=True, exist_ok=False)
    (directorio / "resultados.json").write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    resumen = reporte["resumen"]
    lineas = [
        "# HU-07 · Corrida del banco",
        "",
        f"Modo: **{reporte['modo']}**.",
        "",
        "El modo HTTP no certifica por sí solo que el backend use un LLM real.",
        "Las pruebas simuladas no son resultados de evaluación del LLM.",
        "",
        f"Construcciones conformes: **{resumen['conformes']}/30** (meta ≥26).",
        f"Declinaciones correctas: **{resumen['declinaciones_correctas']}/10** (meta ≥8).",
        f"Errores silenciosos: **{resumen['errores_silenciosos']}**.",
        f"Registros confirmados: **{resumen['registros_confirmados']}/40**.",
        "",
        "## Resumen por familia",
        "",
        "| Familia | Pos. | Neg. | Conforme | Geom. no conforme | Decl. explícita | "
        "Decl. indebida | Fallo técnico | Silenciosos |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for familia, conteo in resumen["por_familia"].items():
        claves = ("positivos", "negativos", *CATEGORIAS, "errores_silenciosos")
        lineas.append("| " + " | ".join([familia, *(str(conteo[k]) for k in claves)]) + " |")
    lineas += [
        "",
        "## Resultados por caso",
        "",
        "| Caso | Familia | Clasificación | Causa | Registro | STEP |",
        "|---|---|---|---|---|---|",
    ]
    for fila in reporte["casos"]:
        estado = "confirmado" if fila["registro_confirmado"] else "no confirmado"
        registro = f"[{estado}]({fila['registro_url']})"
        step = fila["step"]
        if step.startswith("http"):
            step = f"[STEP]({step})"
        lineas.append(
            "| "
            + " | ".join(
                _celda(v)
                for v in (
                    fila["id"],
                    fila["familia"],
                    fila["categoria"],
                    fila["causa"],
                    registro,
                    step,
                )
            )
            + " |"
        )
    lineas += [
        "",
        "Los valores medidos y las desviaciones por eje están en [resultados.json]"
        "(resultados.json).",
        "",
        "Una declinación correcta requiere negativo del banco, señal explícita del pipeline "
        "y motivo no vacío; no se exige coincidencia literal del motivo ni se certifica su "
        "equivalencia semántica automática.",
        "Un error silencioso es una construcción aceptada por la API que incumple la "
        "referencia geométrica o construye un caso negativo.",
        "",
        "## Seguimiento",
        "",
        "HU-07 no se declara completada. Si falla una meta, revisar las causas por caso, "
        "documentar un ajuste y repetir una sola vez conservando ambas corridas. "
        "Esta herramienta no ajusta prompts ni reintenta automáticamente.",
    ]
    (directorio / "reporte.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def ejecutar(cliente, *, banco=DEFAULT_PATH, salida=Path("docs/hu07"), simulado=False):
    casos = read_dataset(banco)
    validate_dataset(casos)
    identificador = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    reporte = {
        "corrida_id": identificador,
        "modo": "SIMULADO — no evaluación LLM" if simulado else "HTTP",
        "fecha_utc": datetime.now(UTC).isoformat(),
        "banco_sha256": hashlib.sha256(Path(banco).read_bytes()).hexdigest(),
        "tolerancia_relativa": TOLERANCIA,
        "casos": [evaluar_caso(cliente, caso) for caso in casos],
    }
    reporte["resumen"] = resumir(reporte["casos"])
    directorio = Path(salida) / identificador
    guardar_reporte(reporte, directorio)
    return reporte, directorio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--salida", type=Path, default=Path("docs/hu07"))
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout debe ser positivo y finito")
    with httpx.Client(base_url=args.api_url.rstrip("/"), timeout=args.timeout) as cliente:
        reporte, directorio = ejecutar(cliente, salida=args.salida)
    print(f"Reporte: {directorio / 'reporte.md'}")
    resumen = reporte["resumen"]
    return 0 if resumen["cumple_metas"] and resumen["registros_confirmados"] == 40 else 2


if __name__ == "__main__":
    raise SystemExit(main())
