"""CLI de releases automáticos: cálculo, changelog y verificación sin publicar (SPEC-056)."""

from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
releases = importlib.import_module("m2_cad.releases")

RUTA_CHANGELOG = releases.RUTA_CHANGELOG
RUTA_PYPROJECT = releases.RUTA_PYPROJECT
actualizar_changelog = releases.actualizar_changelog
analizar_commit = releases.analizar_commit
analizar_commits = releases.analizar_commits
es_convencional = releases.es_convencional
generar_seccion = releases.generar_seccion
hay_versionamiento = releases.hay_versionamiento
leer_version_pyproject = releases.leer_version_pyproject
normalizar_version = releases.normalizar_version
siguiente_version = releases.siguiente_version
sincronizar_version_pyproject = releases.sincronizar_version_pyproject
versiones_coinciden = releases.versiones_coinciden

SIN_CAMBIOS = 2


def ejecutar_git(*argumentos: str) -> str | None:
    resultado = subprocess.run(
        ["git", *argumentos],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode != 0:
        return None
    return resultado.stdout.strip()


def ultima_etiqueta() -> str | None:
    etiquetas = ejecutar_git("tag", "--list", "v*", "--sort=-version:refname")
    return etiquetas.splitlines()[0] if etiquetas else None


def referencia_existe(referencia: str | None) -> bool:
    if not referencia:
        return False
    return ejecutar_git("rev-parse", "--verify", "--quiet", f"{referencia}^{{commit}}") is not None


def mensajes_desde(referencia: str | None) -> list[str]:
    if not referencia_existe(referencia):
        return []
    formato = "%H%x1f%s%x1f%b%x1e"
    salida = ejecutar_git("log", f"--format={formato}", f"{referencia}..HEAD")
    if not salida:
        return []
    mensajes = []
    for registro in salida.split("\x1e"):
        campos = registro.strip("\n").split("\x1f")
        if len(campos) < 2:
            continue
        mensaje = campos[1].strip()
        if len(campos) > 2 and campos[2].strip():
            mensaje += "\n" + campos[2].strip()
        mensajes.append(mensaje)
    return mensajes


def archivos_desde(referencia: str | None) -> list[str]:
    if not referencia_existe(referencia):
        return []
    salida = ejecutar_git("diff", "--name-only", f"{referencia}..HEAD")
    return salida.splitlines() if salida else []


def contexto(desde: str | None) -> tuple[str, str | None, list, list[str]]:
    etiqueta = desde or ultima_etiqueta()
    try:
        base = normalizar_version(etiqueta or "")
    except ValueError:
        base = leer_version_pyproject((RAIZ / RUTA_PYPROJECT).read_text(encoding="utf-8"))
    referencia = etiqueta if referencia_existe(etiqueta) else None
    mensajes = mensajes_desde(referencia)
    return base, referencia, analizar_commits(mensajes), archivos_desde(referencia)


def proposicion(
    desde: str | None, fecha: str | None
) -> tuple[str, str, list, list[str], str, bool]:
    base, referencia, commits, archivos = contexto(desde)
    version = siguiente_version(base, commits, archivos)
    seccion = generar_seccion(version, commits, fecha=fecha, archivos=archivos)
    return base, referencia, commits, archivos, seccion, hay_versionamiento(commits)


def modo_dry_run(desde: str | None, fecha: str | None) -> int:
    base, referencia, commits, _, seccion, cambios = proposicion(desde, fecha)
    origen = referencia or "la versión actual de pyproject.toml"
    print(f"Versión base ({origen}): {base}")
    print(f"Commits convencionales: {len(commits)}")
    if not cambios:
        print("Sin cambios que requieran versión; no se publicaría release.")
        return 0
    version = seccion.splitlines()[0].split("[v", 1)[1].split("]", 1)[0]
    print(f"Versión propuesta: {version}")
    print("Etiquetas creadas: ninguna; releases publicadas: ninguna.")
    print("--- CHANGELOG PROPUESTO ---")
    print(seccion, end="")
    return 0


def modo_version(desde: str | None) -> int:
    _, _, _, _, seccion, _ = proposicion(desde, None)
    print(seccion.splitlines()[0].split("[v", 1)[1].split("]", 1)[0])
    return 0


def modo_preparar(desde: str | None, fecha: str | None, ruta_notas: Path) -> int:
    _, _, commits, _, seccion, cambios = proposicion(desde, fecha)
    if not cambios:
        print("SIN_CAMBIOS: no hay commits que requieran una nueva versión.")
        return SIN_CAMBIOS
    version = seccion.splitlines()[0].split("[v", 1)[1].split("]", 1)[0]
    ruta_pyproject = RAIZ / RUTA_PYPROJECT
    ruta_changelog = RAIZ / RUTA_CHANGELOG
    previo = ruta_changelog.read_text(encoding="utf-8") if ruta_changelog.exists() else ""
    ruta_changelog.write_text(actualizar_changelog(previo, seccion), encoding="utf-8", newline="\n")
    ruta_pyproject.write_text(
        sincronizar_version_pyproject(ruta_pyproject.read_text(encoding="utf-8"), version),
        encoding="utf-8",
        newline="\n",
    )
    ruta_notas.write_text(seccion, encoding="utf-8", newline="\n")
    print(f"PREPARADO v{version} ({len(commits)} commits); etiqueta y release sin crear.")
    return 0


def modo_verificar() -> int:
    ruta_pyproject = RAIZ / RUTA_PYPROJECT
    version = leer_version_pyproject(ruta_pyproject.read_text(encoding="utf-8"))
    etiqueta = ultima_etiqueta()
    if etiqueta and not versiones_coinciden(etiqueta, ruta_pyproject.read_text(encoding="utf-8")):
        print(f"Versión {version} no coincide con la etiqueta {etiqueta}.", file=sys.stderr)
        return 1
    if not etiqueta:
        print("Sin etiqueta alcanzable: se omite la comparación etiqueta/pyproject.")
    ruta_changelog = RAIZ / RUTA_CHANGELOG
    changelog = ruta_changelog.read_text(encoding="utf-8") if ruta_changelog.exists() else ""
    if f"## [v{version}]" not in changelog:
        print(f"CHANGELOG.md no contiene la sección v{version}.", file=sys.stderr)
        return 1
    print(f"Coherencia verificada: pyproject y CHANGELOG en v{version}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument("--dry-run", action="store_true", help="Muestra la propuesta sin escribir.")
    modo.add_argument("--verificar", action="store_true", help="Comprueba versión y changelog.")
    modo.add_argument("--preparar", action="store_true", help="Escribe changelog y versión.")
    modo.add_argument("--version", action="store_true", help="Imprime la versión propuesta.")
    modo.add_argument("--titulo", nargs="?", const="__ENV__", help="Valida un título conventional.")
    parser.add_argument("--desde", help="Versión o ref base; por defecto, última etiqueta.")
    parser.add_argument("--fecha", help="Fecha ISO de la entrada del changelog.")
    parser.add_argument("--notas", type=Path, default=Path(".release-notes.md"))
    argumentos = parser.parse_args(argv)

    if argumentos.titulo is not None:
        titulo = (
            os.environ.get("PR_TITLE", "") if argumentos.titulo == "__ENV__" else argumentos.titulo
        )
        if not es_convencional(titulo):
            print(f"Título de PR no convencional: {titulo}", file=sys.stderr)
            return 1
        print(f"Título convencional: {analizar_commit(titulo).etiqueta()}")
        return 0
    if argumentos.verificar:
        return modo_verificar()
    if argumentos.version:
        return modo_version(argumentos.desde)
    if argumentos.preparar:
        return modo_preparar(argumentos.desde, argumentos.fecha, argumentos.notas)
    return modo_dry_run(argumentos.desde, argumentos.fecha)


if __name__ == "__main__":
    raise SystemExit(main())
