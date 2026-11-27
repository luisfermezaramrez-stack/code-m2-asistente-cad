"""Cálculo determinista de versiones y changelog desde Conventional Commits (SPEC-056)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

RUTA_CHANGELOG = Path("CHANGELOG.md")
RUTA_PYPROJECT = Path("pyproject.toml")
RUTAS_CONTRATO = ("contracts/openapi-v1.json", "frontend/src/generated/api.ts")

TIPOS: dict[str, str] = {
    "feat": "Nuevas funcionalidades",
    "fix": "Correcciones",
    "perf": "Rendimiento",
    "refactor": "Refactorizaciones",
    "docs": "Documentación",
    "style": "Estilo",
    "test": "Pruebas",
    "build": "Construcción",
    "ci": "Integración continua",
    "chore": "Mantenimiento",
}

RE_CABECERA = re.compile(
    r"^(?P<tipo>[a-z]+)(?:\((?P<alcance>[^)]+)\))?(?P<ruptura>!)?: (?P<descripcion>.+)$"
)
RE_RUPTURA = re.compile(r"^BREAKING CHANGE:\s*(?P<detalle>.+)$", re.MULTILINE)
RE_VERSION = re.compile(r"^(?P<mayor>\d+)\.(?P<menor>\d+)\.(?P<parche>\d+)$")
RE_ETIQUETA = re.compile(r"^v?(?P<mayor>\d+)\.(?P<menor>\d+)(?:\.(?P<parche>\d+))?$")
RE_VERSION_PYPROJECT = re.compile(r'(?m)^version\s*=\s*"([^"]+)"')
RECCIONES_VERSION = ("feat", "fix", "perf")


@dataclass(frozen=True)
class CommitConvencional:
    tipo: str
    alcance: str | None
    descripcion: str
    ruptura: bool
    detalle_ruptura: str | None = None

    def etiqueta(self) -> str:
        if self.alcance:
            return f"{self.tipo}({self.alcance})"
        return self.tipo


def analizar_commit(mensaje: str) -> CommitConvencional:
    lineas = mensaje.strip().splitlines()
    if not lineas:
        raise ValueError("El commit está vacío")
    coincidencia = RE_CABECERA.match(lineas[0])
    if not coincidencia:
        raise ValueError(f"Commit no convencional: {lineas[0]}")
    tipo = coincidencia.group("tipo")
    if tipo not in TIPOS:
        raise ValueError(f"Tipo de commit desconocido: {tipo}")
    cuerpo = "\n".join(lineas[1:])
    ruptura = coincidencia.group("ruptura") == "!" or bool(RE_RUPTURA.search(cuerpo))
    coincidencia_ruptura = RE_RUPTURA.search(cuerpo)
    detalle = coincidencia_ruptura.group("detalle").strip() if coincidencia_ruptura else None
    return CommitConvencional(
        tipo=tipo,
        alcance=coincidencia.group("alcance"),
        descripcion=coincidencia.group("descripcion").strip(),
        ruptura=ruptura,
        detalle_ruptura=detalle,
    )


def es_convencional(mensaje: str) -> bool:
    try:
        analizar_commit(mensaje)
    except ValueError:
        return False
    return True


def analizar_commits(mensajes: Iterable[str]) -> list[CommitConvencional]:
    return [analizar_commit(mensaje) for mensaje in mensajes if es_convencional(mensaje)]


def normalizar_version(valor: str) -> str:
    texto = valor.strip()
    coincidencia = RE_VERSION.match(texto) or RE_ETIQUETA.match(texto)
    if not coincidencia:
        raise ValueError(f"Versión no válida: {valor}")
    parche = coincidencia.group("parche") or "0"
    return f"{coincidencia.group('mayor')}.{coincidencia.group('menor')}.{parche}"


def toca_contrato(archivos: Iterable[str]) -> bool:
    for archivo in archivos:
        normalizado = archivo.replace("\\", "/")
        if any(ruta in normalizado for ruta in RUTAS_CONTRATO):
            return True
    return False


def siguiente_version(
    actual: str, commits: Iterable[CommitConvencional], archivos: Iterable[str] = ()
) -> str:
    mayor, menor, parche = (int(parte) for parte in normalizar_version(actual).split("."))
    lista = list(commits)
    if not lista:
        return f"{mayor}.{menor}.{parche}"
    if any(commit.ruptura for commit in lista):
        return f"{mayor + 1}.0.0"
    if any(commit.tipo == "feat" for commit in lista):
        return f"{mayor}.{menor + 1}.0"
    if any(commit.tipo in ("fix", "perf") for commit in lista):
        return f"{mayor}.{menor}.{parche + 1}"
    return f"{mayor}.{menor}.{parche}"


def hay_versionamiento(commits: Iterable[CommitConvencional]) -> bool:
    return any(commit.tipo in RECCIONES_VERSION or commit.ruptura for commit in commits)


def formatear_cambio(commit: CommitConvencional) -> str:
    return f"- **{commit.etiqueta()}**: {commit.descripcion}"


def generar_seccion(
    version: str,
    commits: Iterable[CommitConvencional],
    fecha: str | None = None,
    archivos: Iterable[str] = (),
) -> str:
    lista = list(commits)
    lineas = [f"## [v{normalizar_version(version)}] - {fecha or date.today().isoformat()}", ""]
    rupturas = [commit for commit in lista if commit.ruptura]
    if rupturas:
        lineas.extend(["### Cambios incompatibles", ""])
        for commit in rupturas:
            detalle = commit.detalle_ruptura or commit.descripcion
            prefijo = "BREAKING CHANGE: " if commit.detalle_ruptura else ""
            lineas.append(f"- **{commit.etiqueta()}**: {prefijo}{detalle}")
        if toca_contrato(archivos):
            lineas.append("- El contrato `/v1` cambia de forma incompatible (SPEC-032).")
        lineas.append("")
    for tipo, titulo in TIPOS.items():
        seleccionados = [
            commit for commit in lista if commit.tipo == tipo and commit not in rupturas
        ]
        if not seleccionados:
            continue
        lineas.extend([f"### {titulo}", ""])
        lineas.extend(formatear_cambio(commit) for commit in seleccionados)
        lineas.append("")
    return "\n".join(lineas).rstrip() + "\n"


def actualizar_changelog(previo: str, seccion: str) -> str:
    cabecera = seccion.splitlines()[0]
    if cabecera in previo:
        return previo
    texto = previo.strip()
    if not texto:
        return "# Changelog\n\nTodos los cambios notables del proyecto.\n\n" + seccion
    lineas = texto.splitlines()
    indice = next((i for i, linea in enumerate(lineas) if linea.startswith("## [")), len(lineas))
    nuevas = lineas[:indice] + seccion.rstrip().splitlines() + [""] + lineas[indice:]
    return "\n".join(nuevas).rstrip() + "\n"


def leer_version_pyproject(contenido: str) -> str:
    coincidencia = RE_VERSION_PYPROJECT.search(contenido)
    if not coincidencia:
        raise ValueError("pyproject.toml no declara version")
    return normalizar_version(coincidencia.group(1))


def sincronizar_version_pyproject(contenido: str, version: str) -> str:
    if not RE_VERSION_PYPROJECT.search(contenido):
        raise ValueError("pyproject.toml no declara version")
    return RE_VERSION_PYPROJECT.sub(
        f'version = "{normalizar_version(version)}"', contenido, count=1
    )


def versiones_coinciden(etiqueta: str, contenido_pyproject: str) -> bool:
    return normalizar_version(etiqueta) == leer_version_pyproject(contenido_pyproject)
