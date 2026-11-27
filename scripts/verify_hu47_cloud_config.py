"""Valida la configuración cloud versionada sin red, Docker ni secretos impresos."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
COMPOSE = RAIZ / "docker-compose.cloud.yml"
CADDYFILE = RAIZ / "deploy" / "Caddyfile"
RUNBOOK = RAIZ / "docs" / "runbook-cloud.md"
DOMINIO = re.compile(r"^(?!-)[a-z0-9-]+(?:\.[a-z0-9-]+)+$")
MARCADORES = ("<", ">", "CAMBIAR", "PLACEHOLDER", "RELLENAR")


def leer(ruta: Path) -> str:
    """Lee un archivo versionado como UTF-8."""
    return ruta.read_text(encoding="utf-8")


def bloque_servicio(texto: str, nombre: str) -> str:
    """Devuelve el bloque indentado de un servicio del Compose."""
    lineas = texto.splitlines()
    for indice, linea in enumerate(lineas):
        if linea != f"  {nombre}:":
            continue
        bloque: list[str] = []
        for otra in lineas[indice + 1 :]:
            if otra and not otra.startswith(" "):
                break
            if otra.startswith("  ") and not otra.startswith("    ") and otra.endswith(":"):
                break
            bloque.append(otra)
        return "\n".join(bloque)
    return ""


def revisar_estructura() -> list[str]:
    """Comprueba invariantes de los archivos que se versionan."""
    errores: list[str] = []
    compose = leer(COMPOSE)
    caddyfile = leer(CADDYFILE)
    runbook = leer(RUNBOOK)

    requeridos_compose = (
        "name: m2-cad-cloud",
        "image: ${M2_IMAGE:?Defina M2_IMAGE}",
        "M2_CORS_ORIGINS: https://${M2_DOMAIN:?Defina M2_DOMAIN}",
        'M2_AUTH_ENABLED: "1"',
        'M2_AUTH_COOKIE_SECURE: "1"',
        'M2_COLA_HABILITADA: "1"',
        "M2_COLA_PATH: /app/data/cola.json",
        "MLFLOW_TRACKING_ENABLED: ${MLFLOW_TRACKING_ENABLED:-0}",
        "condition: service_healthy",
        "m2-cad-data:/app/data",
        "m2-cad-outputs:/app/outputs",
    )
    for texto in requeridos_compose:
        if texto not in compose:
            errores.append(f"docker-compose.cloud.yml: falta {texto}")

    api = bloque_servicio(compose, "m2-cad")
    worker = bloque_servicio(compose, "m2-cad-worker")
    if not api or not worker:
        errores.append("docker-compose.cloud.yml: faltan los servicios m2-cad y m2-cad-worker")
    if "ports:" in api:
        errores.append("m2-cad no debe publicar puertos de host; Caddy termina TLS")
    if "m2_cad.worker" not in worker:
        errores.append("m2-cad-worker no ejecuta python -m m2_cad.worker")
    if "condition: service_healthy" not in worker:
        errores.append("m2-cad-worker debe esperar a que la API esté healthy")
    for volumen in ("  m2-cad-data:", "  m2-cad-outputs:"):
        if volumen not in compose:
            errores.append(f"docker-compose.cloud.yml: falta el volumen {volumen.strip()}")

    for texto in (
        "{$M2_DOMAIN}",
        "{$M2_TLS_EMAIL}",
        "reverse_proxy m2-cad:8000",
        "flush_interval -1",
    ):
        if texto not in caddyfile:
            errores.append(f"Caddyfile: falta {texto}")
    if "auto_https off" in caddyfile:
        errores.append("Caddyfile no debe desactivar HTTPS automático")
    for texto in ("/v1/health", "rollback", "rotación", "smoke_deploy.py"):
        if texto not in runbook:
            errores.append(f"runbook-cloud.md: falta {texto}")
    return errores


def valor_sin_marcador(nombre: str, minimo: int) -> bool:
    """Comprueba que una variable exista y no parezca un ejemplo."""
    valor = os.getenv(nombre, "").strip()
    return len(valor) >= minimo and not any(m in valor.upper() for m in MARCADORES)


def revisar_entorno() -> list[str]:
    """Comprueba la configuración de publicación sin mostrar valores secretos."""
    errores: list[str] = []
    imagen = os.getenv("M2_IMAGE", "").strip()
    if not valor_sin_marcador("M2_IMAGE", 3) or ":" not in imagen:
        errores.append("M2_IMAGE: falta una referencia de imagen con etiqueta o digest")

    dominio = os.getenv("M2_DOMAIN", "").strip().lower().rstrip("/")
    if (
        not dominio
        or "://" in dominio
        or "*" in dominio
        or "/" in dominio
        or not DOMINIO.fullmatch(dominio)
    ):
        errores.append("M2_DOMAIN: se espera un hostname sin esquema, puerto ni comodín")

    correo = os.getenv("M2_TLS_EMAIL", "").strip()
    if correo.count("@") != 1 or "." not in correo.split("@")[-1]:
        errores.append("M2_TLS_EMAIL: se espera una dirección de administración")

    for nombre, minimo in (
        ("DEEPSEEK_API_KEY", 8),
        ("M2_DOWNLOAD_SECRET", 32),
        ("M2_AUTH_SECRET", 32),
    ):
        if not valor_sin_marcador(nombre, minimo):
            errores.append(f"{nombre}: valor ausente, corto o de ejemplo")

    usuarios = os.getenv("M2_AUTH_USERS", "").strip()
    try:
        datos = json.loads(usuarios) if usuarios else {}
        validos = isinstance(datos, dict) and any(
            isinstance(hash_clave, str) and hash_clave.startswith("pbkdf2_sha256$")
            for hash_clave in datos.values()
        )
    except ValueError:
        validos = False
    if not validos:
        errores.append("M2_AUTH_USERS: se espera JSON con al menos un hash pbkdf2_sha256")
    return errores


def principales() -> list[str]:
    """Lista lo que no puede verificarse en local."""
    return [
        "proveedor y cuenta autorizados",
        "DNS del dominio propio",
        "certificado TLS emitido por Caddy",
        "imagen publicada en un registro accesible",
        "AC1 a AC4 en el entorno desplegado",
    ]


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de la validación local."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modo", choices=("plantilla", "produccion"), default="plantilla")
    args = parser.parse_args(argv)

    errores = revisar_estructura()
    if args.modo == "produccion":
        errores.extend(revisar_entorno())

    if errores:
        for error in errores:
            print(f"ERROR: {error}")
        return 1

    print("Configuración cloud consistente; no se hizo red ni se mostraron secretos.")
    print("Pendiente para publicar:" + ";".join(principales()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
