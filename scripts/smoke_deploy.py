"""Prueba de humo y latencia del servicio desplegado (HU-10, AC3/AC4).

Envía solicitudes del banco HU-02 a `POST /v1/generar` de forma secuencial, mide la
latencia del lado del cliente y escribe `smoke.csv` (una fila por solicitud) y
`smoke.json` (resumen con p50/p90). Gasta tokens de DeepSeek: cada solicitud es real.

Si la API exige sesión (HU-53), entra con `--usuario` (o `M2_SMOKE_USUARIO`) y la clave
de `M2_SMOKE_CLAVE`, que nunca se pasa por la línea de comandos. Sin credenciales válidas
termina con código 2 antes de generar, sin gastar tokens.

Uso desde la raíz:
    uv run python scripts/smoke_deploy.py --n 5            # humo (AC4)
    uv run python scripts/smoke_deploy.py --n 30           # latencia (AC3)
"""

import argparse
import csv
import json
import math
import os
import sys
import time
from itertools import zip_longest
from pathlib import Path

import httpx

from m2_cad.dataset import read_dataset

COLUMNAS = ("id", "familia", "estado_http", "resultado", "latencia_s", "detalle")
PREFIJO_DECLINACION = "Pieza declinada"
COOKIE_SESION = "m2_sesion"


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


def autenticar(cliente: httpx.Client, usuario: str | None, clave: str | None) -> str | None:
    """Inicia sesión si la API la exige (HU-53); devuelve un error legible o None."""
    try:
        consulta = cliente.get("/v1/auth/me")
    except httpx.HTTPError as exc:
        return f"No se pudo consultar la sesión: {type(exc).__name__}."
    if consulta.status_code >= 500:
        return f"No se pudo consultar la sesión (HTTP {consulta.status_code})."
    try:
        estado = consulta.json()
    except ValueError:
        return None  # API sin sesión: modo local o anterior a HU-53.
    if not isinstance(estado, dict) or not estado.get("requerido"):
        return None
    if not usuario or not clave:
        return "La API exige sesión: indica --usuario y define M2_SMOKE_CLAVE en el entorno."
    url = cliente.base_url
    if url.scheme == "http" and url.host not in {"localhost", "127.0.0.1", "::1"}:
        print(
            f"Aviso: la clave viaja sin cifrar hacia {url.host}; usa HTTPS fuera de esta máquina.",
            file=sys.stderr,
        )
    try:
        respuesta = cliente.post("/v1/auth/login", json={"usuario": usuario, "clave": clave})
    except httpx.HTTPError as exc:
        return f"No se pudo iniciar sesión como {usuario}: {type(exc).__name__}."
    if respuesta.status_code != 200:
        return f"No se pudo iniciar sesión como {usuario} (HTTP {respuesta.status_code})."
    # La cookie es Secure: httpx no la reenvía por HTTP, así que se envía explícita.
    for cabecera in respuesta.headers.get_list("set-cookie"):
        nombre, _, resto = cabecera.partition("=")
        if nombre.strip() == COOKIE_SESION:
            cliente.headers["Cookie"] = f"{COOKIE_SESION}={resto.split(';', 1)[0]}"
            return None
    return "El inicio de sesión no devolvió la cookie de sesión."


def enviar(cliente: httpx.Client, fila: dict) -> dict:
    inicio = time.perf_counter()
    try:
        respuesta = cliente.post("/v1/generar", json={"texto": fila["solicitud"]})
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
    parser.add_argument(
        "--usuario",
        default=os.environ.get("M2_SMOKE_USUARIO"),
        help="usuario HU-53 si la API exige sesión; la clave se lee de M2_SMOKE_CLAVE",
    )
    args = parser.parse_args(argv)

    filas = seleccionar(read_dataset(), args.n, args.ids)
    resultados = []
    with httpx.Client(base_url=args.base_url, timeout=args.timeout, transport=transport) as c:
        error = autenticar(c, args.usuario, os.environ.get("M2_SMOKE_CLAVE"))
        if error:
            print(error, file=sys.stderr)
            return 2
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
