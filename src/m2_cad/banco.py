"""Corrida del banco HU-02 contra el modelo configurado (HU-14, AC6 y AC7).

Cada solicitud pasa por el pipeline completo (modelo -> /dsl/check -> B-rep) y
se compara con la referencia del banco: las positivas deben construirse con
volumen y caja dentro de ±2 %, y las negativas deben declinarse. El resumen da
acierto, tasa de programas que pasan el verificador, latencia, tokens y, si se
pasan los precios, el costo estimado.

Uso (gasta tokens del modelo real):
    uv run python -m m2_cad.banco --ids HU02-P01,HU02-P06,HU02-P11,HU02-P21,HU02-P26
    uv run python -m m2_cad.banco --precio-entrada <USD/1M> --precio-salida <USD/1M>
"""

import argparse
import csv
import json
import math
import re
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from m2_cad import pipeline, seguimiento
from m2_cad.dataset import DEFAULT_PATH, read_dataset

TOLERANCIA = 0.02
CAMPOS = (
    "id",
    "familia",
    "esperado",
    "estado",
    "correcto",
    "latencia_s",
    "tokens_entrada",
    "tokens_salida",
    "detalle",
)
# Estados en los que el modelo entregó un programa que pasó el verificador.
ESTADOS_VERIFICADOS = ("construida", "declinada", "error_construccion")


class ContadorUso:
    """Envuelve llm.chat y acumula los tokens del campo `usage` de cada respuesta."""

    def __init__(self, chat: Callable[..., dict]) -> None:
        self._chat = chat
        self.entrada = 0
        self.salida = 0

    def __call__(self, cuerpo: dict, *, url: str, timeout: float) -> dict:
        respuesta = self._chat(cuerpo, url=url, timeout=timeout)
        uso = respuesta.get("usage") or {}
        self.entrada += int(uso.get("prompt_tokens") or 0)
        self.salida += int(uso.get("completion_tokens") or 0)
        return respuesta


def _dentro_de_tolerancia(resultado: pipeline.ResultadoPieza, esperado: dict) -> bool:
    volumen_ok = math.isclose(resultado.volumen_mm3, esperado["volumen_mm3"], rel_tol=TOLERANCIA)
    caja_ok = all(
        math.isclose(real, referencia, rel_tol=TOLERANCIA, abs_tol=1e-6)
        for real, referencia in zip(resultado.caja_mm, esperado["caja_xyz_mm"], strict=True)
    )
    return volumen_ok and caja_ok


def error_relativo_pct(resultado: pipeline.ResultadoPieza, esperado: dict) -> float | None:
    """Error relativo del volumen construido contra la referencia, en porcentaje."""
    volumen_esperado = float(esperado["volumen_mm3"])
    if not volumen_esperado:
        return None
    return abs(resultado.volumen_mm3 - volumen_esperado) / volumen_esperado * 100


def _seguir_caso(registro: dict, configuracion: seguimiento.Configuracion) -> None:
    """Registra la corrida hija de un caso del banco (HU-16, AC4)."""
    corrida = seguimiento.iniciar_corrida(
        configuracion.experimento_banco,
        nombre=registro["id"],
        anidada=True,
        configuracion=configuracion,
        tags={
            "caso": registro["id"],
            "esperado": registro["esperado"],
            "estado": registro["estado"],
        },
    )
    corrida.registrar_params(caso=registro["id"], familia=registro["familia"])
    corrida.registrar_metricas(
        acierto=int(bool(registro["correcto"])),
        dsl_check_ok=registro["dsl_check_ok"],
        error_relativo_pct=registro["error_relativo_pct"],
        latencia_s=registro["latencia_s"],
    )
    corrida.finalizar()


def evaluar_caso(
    fila: dict,
    *,
    generar: Callable[..., pipeline.ResultadoPieza] | None = None,
    directorio: Path,
    configuracion: seguimiento.Configuracion | None = None,
) -> dict:
    """Corre una solicitud del banco y la clasifica.

    ModeloNoDisponible se propaga: sin modelo el banco se detiene en vez de
    contar fallos que no son del modelo.
    """
    generar = generar or pipeline.generar_pieza
    esperado = fila["resultado_esperado"]
    declinar = esperado == "declinar"
    registro = {"id": fila["id"], "familia": fila["familia"], "esperado": esperado}

    inicio = time.perf_counter()
    relativo = None
    try:
        resultado = generar(fila["solicitud"], directorio=directorio)
    except pipeline.ModeloNoDisponible:
        raise
    except pipeline.PiezaDeclinada as exc:
        estado, correcto, detalle = "declinada", declinar, exc.motivo
    except pipeline.ErrorVerificacion as exc:
        estado, correcto, detalle = "invalido", False, str(exc)
    except pipeline.ErrorGeneracion as exc:
        estado, correcto, detalle = "sin_programa", False, str(exc)
    except Exception as exc:  # noqa: BLE001 - el kernel CAD puede fallar con cualquier tipo
        estado, correcto, detalle = "error_construccion", False, f"{type(exc).__name__}: {exc}"
    else:
        estado = "construida"
        correcto = False
        if not declinar:
            esperado_pieza = json.loads(esperado)
            correcto = _dentro_de_tolerancia(resultado, esperado_pieza)
            relativo = error_relativo_pct(resultado, esperado_pieza)
        detalle = f"volumen={resultado.volumen_mm3:.2f} caja={resultado.caja_mm}"

    registro.update(
        estado=estado,
        correcto=correcto,
        latencia_s=round(time.perf_counter() - inicio, 3),
        detalle=detalle,
        dsl_check_ok=int(estado in ESTADOS_VERIFICADOS),
        error_relativo_pct=relativo,
    )
    if configuracion is not None:
        _seguir_caso(registro, configuracion)
    return registro


def resumir(
    registros: list[dict], *, precio_entrada: float = 0.0, precio_salida: float = 0.0
) -> dict:
    """Agrega acierto, tasa de /dsl/check, latencia media, tokens y costo (USD por 1M)."""
    casos = len(registros) or 1
    entrada = sum(int(r.get("tokens_entrada") or 0) for r in registros)
    salida = sum(int(r.get("tokens_salida") or 0) for r in registros)
    return {
        "casos": len(registros),
        "acierto": sum(bool(r["correcto"]) for r in registros) / casos,
        "tasa_dsl_check": sum(r["estado"] in ESTADOS_VERIFICADOS for r in registros) / casos,
        "latencia_media_s": sum(float(r["latencia_s"]) for r in registros) / casos,
        "tokens_entrada": entrada,
        "tokens_salida": salida,
        "costo_usd": (entrada * precio_entrada + salida * precio_salida) / 1e6,
    }


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Corre el banco HU-02 contra el modelo.")
    parser.add_argument("--banco", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--salida", type=Path, default=Path("outputs/banco"))
    parser.add_argument("--ids", default="", help="IDs separados por coma (por defecto, todos)")
    parser.add_argument("--precio-entrada", type=float, default=0.0, help="USD por 1M tokens")
    parser.add_argument("--precio-salida", type=float, default=0.0, help="USD por 1M tokens")
    return parser.parse_args(argv)


def _acierto(registros: list[dict]) -> float:
    """Proporción de casos correctos del grupo dado (0 si el grupo está vacío)."""
    return sum(bool(r["correcto"]) for r in registros) / len(registros) if registros else 0.0


def _registrar_resumen(padre: seguimiento.Corrida, registros: list[dict], resumen: dict) -> None:
    """Vuelca el resumen del banco como métricas de la corrida padre (AC4)."""
    padre.registrar_metricas(
        acierto=resumen["acierto"],
        acierto_positivas=_acierto([r for r in registros if r["esperado"] != "declinar"]),
        acierto_negativas=_acierto([r for r in registros if r["esperado"] == "declinar"]),
        dsl_check_ok_total=sum(r["dsl_check_ok"] for r in registros),
        latencia_media_s=resumen["latencia_media_s"],
        tokens_entrada=resumen["tokens_entrada"],
        tokens_salida=resumen["tokens_salida"],
        costo_usd=resumen["costo_usd"],
    )


def _abrir_corrida_padre(
    args: argparse.Namespace, filas: list[dict], configuracion: seguimiento.Configuracion
) -> seguimiento.Corrida:
    """Abre la corrida padre del banco y registra la versión de modelo servida (AC4, AC7)."""
    modelo = pipeline.llm.planner_model()
    padre = seguimiento.iniciar_corrida(
        configuracion.experimento_banco,
        nombre=modelo,
        tags={"modelo": modelo, "version_modelo": seguimiento.version_modelo()},
        configuracion=configuracion,
    )
    padre.registrar_params(
        modelo=modelo,
        version_modelo=seguimiento.version_modelo(),
        precio_entrada=args.precio_entrada,
        precio_salida=args.precio_salida,
        n_casos=len(filas),
    )
    referencia = seguimiento.registrar_version_modelo(
        nombre=f"m2-cad-{modelo}",
        version=seguimiento.version_modelo(),
        corrida_id=padre.id,
        fuente=f"runs:/{padre.id}",
        configuracion=configuracion,
        descripcion=f"Configuración servida al banco HU-02: {modelo}",
    )
    padre.registrar_tags(modelo_registrado=referencia)
    return padre


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    filas = read_dataset(args.banco)
    if args.ids:
        elegidos = [i.strip() for i in args.ids.split(",") if i.strip()]
        filas = [fila for fila in filas if fila["id"] in elegidos]

    configuracion = seguimiento.Configuracion.desde_entorno()
    padre = _abrir_corrida_padre(args, filas, configuracion)
    seguimiento_casos = configuracion if padre.activa else None

    contador = ContadorUso(pipeline.llm.chat)
    original = pipeline.llm.chat
    pipeline.llm.chat = contador
    registros = []
    try:
        with tempfile.TemporaryDirectory() as temporal:
            for fila in filas:
                antes = (contador.entrada, contador.salida)
                registro = evaluar_caso(
                    fila, directorio=Path(temporal), configuracion=seguimiento_casos
                )
                registro["tokens_entrada"] = contador.entrada - antes[0]
                registro["tokens_salida"] = contador.salida - antes[1]
                registros.append(registro)
                print(f"{registro['id']}: {registro['estado']} correcto={registro['correcto']}")
    except pipeline.ModeloNoDisponible as exc:
        print(f"Banco detenido: {exc}")
        padre.finalizar(estado="error", error="ModeloNoDisponible")
        return 2
    except BaseException as exc:
        # Cualquier otra interrupción cierra la corrida padre (nunca en RUNNING).
        padre.finalizar(estado="error", error=type(exc).__name__)
        raise
    finally:
        pipeline.llm.chat = original

    resumen = resumir(
        registros, precio_entrada=args.precio_entrada, precio_salida=args.precio_salida
    )
    resumen["modelo"] = pipeline.llm.planner_model()
    _registrar_resumen(padre, registros, resumen)
    padre.finalizar(estado="completado")

    args.salida.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base = args.salida / f"{re.sub(r'[^A-Za-z0-9._-]', '_', resumen['modelo'])}-{marca}"
    with base.with_suffix(".csv").open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows({campo: registro[campo] for campo in CAMPOS} for registro in registros)
    base.with_suffix(".json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    print(json.dumps(resumen, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
