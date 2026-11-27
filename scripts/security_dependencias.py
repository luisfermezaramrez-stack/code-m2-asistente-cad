#!/usr/bin/env python3
"""Auditoría de dependencias Python con pip-audit fijado (SPEC-029, HU-28).

Exporta `uv.lock` con `uv export` (nunca se versiona un `requirements.txt`), quita
los requisitos que apuntan a una ruta local —no auditables desde un índice— y
audita el resto con `pip-audit==2.10.1` lanzado por `uvx`. La severidad de cada
advisory se consulta en la API de OSV; si la consulta falla se clasifica como
`desconocida` y, por lo tanto, bloquea (RF-3, se falla cerrado).

    python scripts/security_dependencias.py                       # sobre uv.lock
    python scripts/security_dependencias.py --auditar req.txt     # fixture o caso puntual
    python scripts/security_dependencias.py --informe informe.json

Códigos de salida: 0 sin hallazgos bloqueantes, 1 con hallazgos bloqueantes,
2 la herramienta no pudo ejecutarse (uv, uvx, red, reporte ilegible).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))

from m2_cad import seguridad_ci  # noqa: E402

TIEMPO_OSV = 20
PREFIJOS_LOCALES = ("file:", "./", "../", "/")


class ErrorHerramienta(Exception):
    """La herramienta externa (uv, uvx o la API de OSV) no pudo completarse."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auditoría de dependencias con pip-audit fijado (SPEC-029, HU-28)."
    )
    parser.add_argument(
        "--informe",
        type=Path,
        help="guarda el JSON crudo de pip-audit en esta ruta",
    )
    parser.add_argument(
        "--auditar",
        type=Path,
        help="audita este archivo de requisitos en vez de exportar uv.lock",
    )
    return parser


def exportar_lock(destino: Path) -> Path:
    """Exporta `uv.lock` a un `requirements.txt` temporal del job (S13, RNF-3)."""
    comando = [
        "uv",
        "export",
        "--locked",
        "--no-dev",
        "--no-emit-project",
        "--format",
        "requirements-txt",
        "--output-file",
        str(destino),
    ]
    try:
        proceso = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True, check=False)
    except OSError as error:
        raise ErrorHerramienta(f"no se pudo ejecutar uv: {error}") from error
    if proceso.returncode != 0:
        raise ErrorHerramienta(
            f"`uv export` falló (código {proceso.returncode}): {proceso.stderr.strip()}"
        )
    if not destino.is_file():
        raise ErrorHerramienta(f"`uv export` no escribió {destino}")
    return destino


def es_requisito_local(linea: str) -> bool:
    """True si la línea del export apunta a una ruta local y no a un índice."""
    texto = linea.strip()
    if not texto or texto.startswith("#"):
        return False
    if texto.startswith("-e "):
        texto = texto[3:].strip()
    referencia = texto.split("@", 1)[1].strip() if "@" in texto else texto
    return referencia.startswith(PREFIJOS_LOCALES)


def filtrar_locales(origen: Path, destino: Path) -> list[str]:
    """Copia solo los requisitos auditables y devuelve los excluidos, nombrados."""
    auditables: list[str] = []
    no_auditables: list[str] = []
    for linea in origen.read_text(encoding="utf-8").splitlines():
        if es_requisito_local(linea):
            no_auditables.append(linea.strip().removeprefix("-e ").strip())
            continue
        auditables.append(linea)
    destino.write_text("\n".join(auditables) + "\n", encoding="utf-8")
    return no_auditables


def auditar(requisitos: Path) -> dict:
    """Corre el pip-audit fijado y devuelve el reporte JSON (código 1 = hallazgos)."""
    comando = [
        "uvx",
        "--from",
        seguridad_ci.ESPECIFICACION_PIP_AUDIT,
        "pip-audit",
        "-r",
        str(requisitos),
        "--no-deps",
        "--disable-pip",
        "--format",
        "json",
    ]
    try:
        proceso = subprocess.run(comando, capture_output=True, text=True, check=False)
    except OSError as error:
        raise ErrorHerramienta(f"no se pudo ejecutar uvx/pip-audit: {error}") from error
    for aviso in (proceso.stderr or "").splitlines():
        if aviso.strip() and not aviso.startswith("WARNING"):
            print(aviso.rstrip(), file=sys.stderr)
    if proceso.returncode not in (0, 1):
        raise ErrorHerramienta(
            f"pip-audit falló (código {proceso.returncode}): {proceso.stderr.strip()}"
        )
    try:
        datos = json.loads(proceso.stdout)
    except json.JSONDecodeError as error:
        raise ErrorHerramienta(f"el reporte de pip-audit no es JSON válido: {error}") from error
    if not isinstance(datos, dict):
        raise ErrorHerramienta("el reporte de pip-audit no tiene la forma esperada (objeto)")
    return datos


def consultar_severidad(advisory: str) -> str:
    """Severidad de un advisory en OSV; cualquier fallo se clasifica `desconocida`."""
    url = f"https://api.osv.dev/v1/vulns/{urllib.parse.quote(advisory)}"
    try:
        with urllib.request.urlopen(url, timeout=TIEMPO_OSV) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as error:
        print(
            f"AVISO: no se pudo consultar OSV para {advisory} ({error}); "
            "se clasifica como desconocida y bloquea.",
            file=sys.stderr,
        )
        return "desconocida"
    if not isinstance(datos, dict):
        return "desconocida"
    return seguridad_ci.severidad_de_osv(datos)


def severidades_de_advisories(auditoria: dict) -> dict[str, str]:
    """Una consulta por advisory (cacheada en la corrida), sin repetir ids."""
    severidades: dict[str, str] = {}
    for dependencia in auditoria.get("dependencies") or []:
        if not isinstance(dependencia, dict):
            continue
        for vuln in dependencia.get("vulns") or []:
            if not isinstance(vuln, dict):
                continue
            advisory = str(vuln.get("id") or "").strip()
            if advisory and advisory not in severidades:
                severidades[advisory] = consultar_severidad(advisory)
    return severidades


def _escanear(argumentos: argparse.Namespace, carpeta: Path) -> int:
    if argumentos.auditar:
        origen = Path(argumentos.auditar)
        if not origen.is_file():
            raise ErrorHerramienta(f"no existe el archivo a auditar: {origen}")
    else:
        origen = exportar_lock(carpeta / "requirements.txt")
    filtrado = carpeta / "requirements-auditables.txt"
    no_auditables = filtrar_locales(origen, filtrado)
    auditoria = auditar(filtrado)
    if argumentos.informe:
        destino = Path(argumentos.informe)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(auditoria, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    excepciones = seguridad_ci.cargar_excepciones(RAIZ / seguridad_ci.RUTA_EXCEPCIONES_DEPENDENCIAS)
    hallazgos = seguridad_ci.clasificar_dependencias(
        auditoria, severidades_de_advisories(auditoria), excepciones, date.today()
    )
    paquetes = auditoria.get("dependencies") or []
    print(
        seguridad_ci.mensaje_dependencias(
            hallazgos, paquetes_auditados=len(paquetes), no_auditables=no_auditables
        )
    )
    return 1 if any(hallazgo.bloqueante for hallazgo in hallazgos) else 0


def main(argv: list[str] | None = None) -> int:
    argumentos = _parser().parse_args(argv)
    try:
        with tempfile.TemporaryDirectory(prefix="m2-security-dependencias-") as carpeta:
            return _escanear(argumentos, Path(carpeta))
    except ErrorHerramienta as error:
        print(f"ERROR: el escaneo de dependencias no pudo ejecutarse: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
