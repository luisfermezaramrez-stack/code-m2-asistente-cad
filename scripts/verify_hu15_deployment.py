"""Arranque HTTP integrado; traductor/modelo SIMULADOS, API/SSE/CAD/archivos reales.

No prueba Docker ni inferencia. Requiere build Vue y el entorno CAD instalado.
Uso desde la raíz: python scripts/verify_hu15_deployment.py --simulate-model
"""

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx


def servir(salidas: Path, puerto: int) -> None:
    import uvicorn

    os.environ["LLM_BASE_URL"] = "http://modelo-simulado-no-contactado"
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ["M2_CORS_ORIGINS"] = f"http://127.0.0.1:{puerto}"
    from m2_cad import api, pipeline

    generar_real = pipeline.generar_pieza

    def generar(texto, *, control):
        def planificar(_):
            if "cancelar" in texto:
                time.sleep(2)  # Llamada bloqueante simulada; no genera progreso del cliente.
            if "declinar" in texto:
                return {"unsupported": "turbina"}
            if "fallar" in texto:
                raise pipeline.ModeloNoDisponible("Proveedor http://10.0.0.9:8080 no disponible")
            return {
                "parts": [{"id": "p", "type": "spacer", "material": "steel", "params": {}}],
                "mates": [],
            }

        return generar_real(
            texto,
            control=control,
            traducir=lambda _: "spacer",
            planificar=planificar,
            directorio=salidas,
        )

    pipeline.generar_pieza = generar
    api.app.dependency_overrides[api.obtener_directorio_salidas] = lambda: salidas
    api.obtener_ruta_registro = lambda: salidas / "registro.csv"
    uvicorn.run(api.app, host="127.0.0.1", port=puerto, log_level="error")


def eventos(response):
    for linea in response.iter_lines():
        if linea.startswith("data: "):
            yield json.loads(linea[6:])


def comprobar(client: httpx.Client, origen: str) -> dict:
    response = client.get("/")
    assert response.status_code == 200 and '<div id="app">' in response.text
    for asset in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', response.text):
        assert client.get(asset).status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/no-existe").headers["content-type"] == "application/json"
    headers = {"Accept": "text/event-stream", "Origin": origen}
    with client.stream("POST", "/generar", json={"texto": "espaciador"}, headers=headers) as stream:
        assert stream.headers["x-accel-buffering"] == "no"
        assert "no-transform" in stream.headers["cache-control"]
        assert "content-encoding" not in stream.headers
        assert stream.headers["access-control-allow-origin"] == origen
        recibidos = list(eventos(stream))
    assert [e["estado"] for e in recibidos] == ["validando", "generando", "verificado"]
    id_ = recibidos[-1]["solicitud_id"]
    tamanos = {}
    for formato in ("step", "glb", "csv"):
        url = f"/generaciones/{id_}/archivos/{formato}"
        assert client.head(url).status_code == 200
        archivo = client.get(url)
        assert archivo.status_code == 200 and archivo.content
        if formato == "glb":
            assert archivo.content[:4] == b"glTF"
        tamanos[formato] = len(archivo.content)

    for texto, esperado in (("declinar turbina", "declinado"), ("fallar proveedor", "error")):
        with client.stream("POST", "/generar", json={"texto": texto}, headers=headers) as stream:
            recibidos = list(eventos(stream))
        assert recibidos[-1]["estado"] == esperado
        assert "10.0.0.9" not in str(recibidos)

    with client.stream(
        "POST", "/generar", json={"texto": "cancelar modelo"}, headers=headers
    ) as stream:
        for evento in eventos(stream):
            if evento["estado"] == "generando":
                # Si hay buffering, el trabajo ya terminó y DELETE no devolverá 202.
                response = client.delete(f"/generaciones/{evento['solicitud_id']}")
                assert response.status_code == 202 and not response.json()["terminal"]
            if evento["terminal"]:
                assert evento["estado"] == "cancelado" and evento["pipeline_detenido"]
                assert not evento["cancelacion_remota_confirmada"]
                break

    with client.stream(
        "POST", "/generar", json={"texto": "cancelar desconexion"}, headers=headers
    ) as stream:
        for evento in eventos(stream):
            if evento["estado"] == "generando":
                id_ = evento["solicitud_id"]
                break
    limite = time.monotonic() + 10
    while time.monotonic() < limite:
        estado = client.get(f"/generaciones/{id_}").json()
        if estado["terminal"]:
            assert estado["estado"] == "cancelado" and estado["pipeline_detenido"]
            break
        time.sleep(0.05)
    else:
        raise AssertionError("La desconexión no alcanzó cancelación cooperativa confirmada")
    return {
        "servicios": "traductor y modelo SIMULADOS",
        "archivos_bytes": tamanos,
        "arranque_nativo": "OK",
        "sse_incremental": "OK",
        "cancelacion_local": "OK",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulate-model", action="store_true")
    parser.add_argument("--serve", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.simulate_model:
        parser.error("Se requiere --simulate-model: este smoke no prueba inferencia real.")
    if args.serve:
        servir(args.serve, args.port)
        return
    raiz = Path(__file__).resolve().parents[1]
    with socket.socket() as socket_libre:
        socket_libre.bind(("127.0.0.1", 0))
        puerto = socket_libre.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="hu15-smoke-") as temporal:
        env = {**os.environ, "PYTHONPATH": str(raiz / "src")}
        proceso = subprocess.Popen(
            [
                sys.executable,
                __file__,
                "--simulate-model",
                "--serve",
                temporal,
                "--port",
                str(puerto),
            ],
            cwd=raiz,
            env=env,
        )
        try:
            origen = f"http://127.0.0.1:{puerto}"
            with httpx.Client(base_url=origen, timeout=15) as client:
                limite = time.monotonic() + 30
                while time.monotonic() < limite:
                    try:
                        if client.get("/health").status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    if proceso.poll() is not None:
                        raise RuntimeError("El servidor de prueba no pudo arrancar")
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Tiempo agotado al arrancar FastAPI")
                print(json.dumps(comprobar(client, origen), ensure_ascii=False))
        finally:
            proceso.terminate()
            proceso.wait(timeout=10)


if __name__ == "__main__":
    main()
