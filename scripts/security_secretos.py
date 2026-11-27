#!/usr/bin/env python3
"""Escaneo de secretos con gitleaks fijado (SPEC-029, HU-28, RF-2, AC1).

Descarga el binario de gitleaks **8.30.1** la primera vez (verificando su sha256),
lo corre sobre el historial del repositorio con `.gitleaks.toml` y traduce el
reporte JSON con `seguridad_ci.mensaje_secretos`: archivo, línea, regla y los tres
pasos permitidos (rotar la clave, retirarla del historial o declarar una excepción
justificada). No usa curl ni wget: solo `urllib` y `tarfile` de la biblioteca
estándar.

    python scripts/security_secretos.py            # todo el historial
    GITLEAKS_LOG_OPTS="-1 HEAD" python ...         # solo el último commit
    GITLEAKS_RUTA=/ruta/al/gitleaks python ...     # binario ya instalado

Códigos de salida: 0 sin hallazgos, 1 hallazgos bloqueantes, 2 la herramienta no
pudo ejecutarse (red, descarga, sistema operativo).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))

from m2_cad import seguridad_ci  # noqa: E402

CONFIG_GITLEAKS = ".gitleaks.toml"
NOMBRE_EN_TAR = "gitleaks"
TIEMPO_DESCARGA = 120


class ErrorHerramienta(Exception):
    """La herramienta externa (descarga o ejecución) no pudo completarse."""


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description="Escaneo de secretos con gitleaks fijado (SPEC-029, HU-28)."
    )


def carpeta_cache() -> Path:
    """Caché del binario: `M2_SECURITY_CACHE` o el directorio temporal del sistema."""
    configurada = os.environ.get("M2_SECURITY_CACHE")
    base = (
        Path(configurada) if configurada else Path(tempfile.gettempdir()) / "m2-cad-security-cache"
    )
    return base


def _descargar_gitleaks(destino: Path) -> Path:
    """Descarga el asset fijado, verifica su sha256 y extrae solo el binario."""
    print(
        f"Descargando gitleaks {seguridad_ci.VERSION_GITLEAKS} desde "
        f"{seguridad_ci.URL_GITLEAKS_LINUX_X64}",
        file=sys.stderr,
    )
    try:
        with urllib.request.urlopen(
            seguridad_ci.URL_GITLEAKS_LINUX_X64, timeout=TIEMPO_DESCARGA
        ) as respuesta:
            contenido = respuesta.read()
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise ErrorHerramienta(f"no se pudo descargar gitleaks: {error}") from error
    huella = hashlib.sha256(contenido).hexdigest()
    if huella != seguridad_ci.SHA256_GITLEAKS_LINUX_X64:
        raise ErrorHerramienta(
            "el sha256 de gitleaks no coincide con la versión fijada: "
            f"esperado {seguridad_ci.SHA256_GITLEAKS_LINUX_X64}, obtenido {huella}"
        )
    try:
        with tarfile.open(fileobj=io.BytesIO(contenido), mode="r:gz") as archivo:
            miembro = archivo.getmember(NOMBRE_EN_TAR)
            if not miembro.isfile():
                raise ErrorHerramienta("el asset de gitleaks no contiene un ejecutable")
            origen = archivo.extractfile(miembro)
            if origen is None:
                raise ErrorHerramienta("no se pudo leer el binario del asset de gitleaks")
            datos = origen.read()
    except (tarfile.TarError, KeyError) as error:
        raise ErrorHerramienta(
            f"el asset de gitleaks no tiene el formato esperado: {error}"
        ) from error
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(datos)
        destino.chmod(0o755)
    except OSError as error:
        raise ErrorHerramienta(f"no se pudo escribir el binario de gitleaks: {error}") from error
    return destino


def resolver_gitleaks() -> Path:
    """Ruta del binario: `GITLEAKS_RUTA`, caché de la versión o descarga verificada."""
    configurada = os.environ.get("GITLEAKS_RUTA")
    if configurada:
        binario = Path(configurada)
        if not binario.is_file():
            raise ErrorHerramienta(f"GITLEAKS_RUTA apunta a un archivo inexistente: {binario}")
        return binario
    destino = carpeta_cache() / seguridad_ci.VERSION_GITLEAKS / NOMBRE_EN_TAR
    if destino.is_file():
        return destino
    return _descargar_gitleaks(destino)


def ejecutar_gitleaks(binario: Path, informe: Path) -> int:
    """Corre gitleaks sobre el historial y deja el reporte JSON en `informe`."""
    configuracion = RAIZ / CONFIG_GITLEAKS
    if not configuracion.is_file():
        raise ErrorHerramienta(f"falta la configuración {configuracion}")
    comando = [
        str(binario),
        "git",
        str(RAIZ),
        "--config",
        str(configuracion),
        "--no-banner",
        "--redact",
        "--report-format",
        "json",
        "--report-path",
        str(informe),
    ]
    opciones = os.environ.get("GITLEAKS_LOG_OPTS", "").strip()
    if opciones:
        comando.extend(["--log-opts", opciones])
    try:
        proceso = subprocess.run(comando, capture_output=True, text=True, check=False)
    except OSError as error:
        raise ErrorHerramienta(f"no se pudo ejecutar gitleaks: {error}") from error
    if proceso.stdout.strip():
        print(proceso.stdout.rstrip(), file=sys.stderr)
    if proceso.stderr.strip():
        print(proceso.stderr.rstrip(), file=sys.stderr)
    return proceso.returncode


def leer_informe(informe: Path) -> list[dict]:
    """Reporte de gitleaks; `[]` si la herramienta no encontró nada."""
    if not informe.is_file():
        return []
    texto = informe.read_text(encoding="utf-8").strip()
    if not texto:
        return []
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as error:
        raise ErrorHerramienta(f"el reporte de gitleaks no es JSON válido: {error}") from error
    if not isinstance(datos, list):
        raise ErrorHerramienta("el reporte de gitleaks no tiene la forma esperada (lista)")
    return [hallazgo for hallazgo in datos if isinstance(hallazgo, dict)]


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    excepciones = seguridad_ci.cargar_excepciones(RAIZ / seguridad_ci.RUTA_EXCEPCIONES_SECRETOS)
    try:
        binario = resolver_gitleaks()
        with tempfile.TemporaryDirectory(prefix="m2-security-secretos-") as carpeta:
            informe = Path(carpeta) / "gitleaks.json"
            codigo = ejecutar_gitleaks(binario, informe)
            hallazgos = leer_informe(informe)
    except ErrorHerramienta as error:
        print(f"ERROR: el escaneo de secretos no pudo ejecutarse: {error}", file=sys.stderr)
        return 2
    # gitleaks sale con 1 cuando reporta hallazgos, aunque una excepción vigente
    # los cubra; cualquier otro código, o un 1 sin reporte, es un fallo de la
    # herramienta y nunca se presenta como escaneo superado.
    if codigo not in (0, 1) or (codigo == 1 and not hallazgos):
        print(
            f"ERROR: gitleaks terminó con código {codigo} sin hallazgos legibles; "
            "el escaneo no puede considerarse superado.",
            file=sys.stderr,
        )
        return 2
    print(seguridad_ci.mensaje_secretos(hallazgos, excepciones=excepciones, hoy=date.today()))
    if seguridad_ci.secretos_bloqueantes(hallazgos, excepciones, date.today()):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
