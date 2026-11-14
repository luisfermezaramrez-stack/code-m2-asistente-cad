"""Prueba de humo y latencia del servicio desplegado (HU-10, AC3/AC4).

Envía solicitudes del banco HU-02 a `POST /generar` de forma secuencial, mide la
latencia del lado del cliente y escribe `smoke.csv` (una fila por solicitud) y
`smoke.json` (resumen con p50/p90). Gasta tokens de DeepSeek: cada solicitud es real.

Uso desde la raíz:
    uv run python scripts/smoke_deploy.py --n 5            # humo (AC4)
    uv run python scripts/smoke_deploy.py --n 30           # latencia (AC3)
"""

import argparse
import csv
import json
import math
import sys
import time
from itertools import zip_longest
from pathlib import Path

import httpx

from m2_cad.dataset import read_dataset

COLUMNAS = ("id", "familia", "estado_http", "resultado", "latencia_s", "detalle")
PREFIJO_DECLINACION = "Pieza declinada"


def seleccionar(filas: list[dict], n: int, ids: list[str] | None = None) -> list[dict]:
    """Elige las filas por id, o alternando familias para cubrirlas todas pronto."""
    if ids:
        por_id = {fila["id"]: fila for fila in filas}
        faltantes = [i for i in ids if i not in por_id]
        if faltantes:
            raise ValueError(f"IDs inexistentes en el banco: {', '.join(faltantes)}")
        return [por_id[i] for i in ids]
    grupos: dict[str, list[dict]] = {}
    for fila in filas:
        grupos.setdefault(fila["familia"], []).append(fila)
    alternadas = [f for ronda in zip_longest(*grupos.values()) for f in ronda if f is not None]
    return alternadas[:n]


def percentil(valores: list[float], p: float) -> float:
    """Percentil por rango más cercano (sin interpolar)."""
    ordenados = sorted(valores)
    rango = max(1, math.ceil(p / 100 * len(ordenados)))
    return ordenados[rango - 1]


def clasificar(respuesta: httpx.Response) -> tuple[str, str]:
    """`pieza`, `declinada` (422 con motivo) o `error`, con el detalle recibido."""
    try:
        cuerpo = respuesta.json()
    except ValueError:
        cuerpo = {}
    detalle = cuerpo.get("detail", "") if isinstance(cuerpo, dict) else ""
    if respuesta.status_code == 200:
        return "pieza", ""
    if (
        respuesta.status_code == 422
        and isinstance(detalle, str)
        and detalle.startswith(PREFIJO_DECLINACION)
    ):
        return "declinada", detalle
    return "error", json.dumps(detalle, ensure_ascii=False) if detalle else respuesta.text[:200]


def enviar(cliente: httpx.Client, fila: dict) -> dict:
    inicio = time.perf_counter()
    try:
        respuesta = cliente.post("/generar", json={"texto": fila["solicitud"]})
        estado_http = str(respuesta.status_code)
        resultado, detalle = clasificar(respuesta)
    except httpx.HTTPError as exc:
        estado_http, resultado, detalle = "", "error", f"{type(exc).__name__}: {exc}"
    return {
        "id": fila["id"],
        "familia": fila["familia"],
        "estado_http": estado_http,
        "resultado": resultado,
        "latencia_s": round(time.perf_counter() - inicio, 3),
        "detalle": detalle,
    }


def resumir(resultados: list[dict], base_url: str) -> dict:
    latencias = [r["latencia_s"] for r in resultados]
    return {
        "base_url": base_url,
        "n": len(resultados),
        "validas": sum(r["resultado"] != "error" for r in resultados),
        "piezas": sum(r["resultado"] == "pieza" for r in resultados),
        "declinadas": sum(r["resultado"] == "declinada" for r in resultados),
        "p50_s": percentil(latencias, 50) if latencias else None,
        "p90_s": percentil(latencias, 90) if latencias else None,
        "max_s": max(latencias) if latencias else None,
    }


def guardar(resultados: list[dict], resumen: dict, salida: Path) -> None:
    salida.mkdir(parents=True, exist_ok=True)
    with (salida / "smoke.csv").open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(resultados)
    (salida / "smoke.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None, transport: httpx.BaseTransport | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--n", type=int, default=5, help="cantidad de solicitudes del banco")
    parser.add_argument("--ids", nargs="+", help="ids concretos del banco (ignora --n)")
    parser.add_argument("--salida", type=Path, default=Path("outputs/smoke"))
    parser.add_argument("--timeout", type=float, default=180.0, help="segundos por solicitud")
    args = parser.parse_args(argv)

    filas = seleccionar(read_dataset(), args.n, args.ids)
    resultados = []
    with httpx.Client(base_url=args.base_url, timeout=args.timeout, transport=transport) as c:
        for indice, fila in enumerate(filas, start=1):
            resultado = enviar(c, fila)
            resultados.append(resultado)
            print(
                f"[{indice}/{len(filas)}] {resultado['id']} {resultado['familia']}: "
                f"{resultado['resultado']} ({resultado['estado_http'] or 'sin respuesta'}) "
                f"{resultado['latencia_s']:.1f} s",
                flush=True,
            )

    resumen = resumir(resultados, args.base_url)
    guardar(resultados, resumen, args.salida)
    print(
        f"Válidas {resumen['validas']}/{resumen['n']} · p50 {resumen['p50_s']} s · "
        f"p90 {resumen['p90_s']} s · resultados en {args.salida}"
    )
    return 0 if resumen["validas"] == resumen["n"] else 1


if __name__ == "__main__":
    sys.exit(main())
