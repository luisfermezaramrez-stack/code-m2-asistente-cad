from __future__ import annotations

import re
import shutil
from pathlib import Path
from urllib.parse import unquote

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "docs-build"
ENLACE = re.compile(r"\]\(([^)]+)\)")
EVIDENCIA_HU07 = "docs/hu07/"


def destino_relativo(ruta: Path) -> Path | None:
    try:
        return ruta.resolve().relative_to(RAIZ.resolve())
    except ValueError:
        return None


def incluida(relativa: Path) -> bool:
    if relativa.suffix.lower() != ".md":
        return False
    texto = relativa.as_posix()
    return relativa.parent == Path(".") or texto.startswith(("docs/", "specs/"))


def objetivo_enlace(crudo: str) -> str | None:
    valor = crudo.strip()
    if valor.startswith("<"):
        final = valor.find(">")
        if final == -1:
            return None
        valor = valor[1:final]
    else:
        valor = valor.split()[0] if valor else ""
    if not valor or valor.startswith(("#", "http://", "https://", "mailto:", "data:")):
        return None
    return unquote(valor.split("#", 1)[0].split("?", 1)[0])


def transformar(texto: str, origen: Path, relativa: Path) -> tuple[str, set[Path]]:
    recursos: set[Path] = set()

    def reemplazar(match: re.Match[str]) -> str:
        crudo = match.group(1)
        objetivo = objetivo_enlace(crudo)
        if objetivo is None:
            return match.group(0)
        destino = (origen.parent / objetivo).resolve()
        rel_destino = destino_relativo(destino)
        if destino.is_file():
            if rel_destino is not None and not incluida(rel_destino):
                recursos.add(rel_destino)
            return match.group(0)
        if objetivo.lower().endswith(".step") and relativa.as_posix().startswith(EVIDENCIA_HU07):
            return f"`{objetivo}`"
        return match.group(0)

    return ENLACE.sub(reemplazar, texto), recursos


def principal() -> None:
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    DESTINO.mkdir(parents=True)

    fuentes = sorted(
        ruta
        for ruta in RAIZ.rglob("*.md")
        if ".git" not in ruta.parts
        and "docs-build" not in ruta.parts
        and ".site" not in ruta.parts
        and incluida(destino_relativo(ruta) or Path())
    )
    recursos: set[Path] = set()

    for fuente in fuentes:
        relativa = destino_relativo(fuente)
        if relativa is None:
            continue
        texto, encontrados = transformar(fuente.read_text(encoding="utf-8"), fuente, relativa)
        recursos.update(encontrados)
        salida = DESTINO / relativa
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto, encoding="utf-8")

    for relativa in sorted(recursos):
        origen = RAIZ / relativa
        if not origen.is_file():
            continue
        salida = DESTINO / relativa
        salida.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, salida)

    print(f"staging: {len(fuentes)} Markdown, {len(recursos)} recursos enlazados")


if __name__ == "__main__":
    principal()
