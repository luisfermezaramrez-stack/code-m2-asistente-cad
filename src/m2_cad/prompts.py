"""Carga y verificación de los prompts versionados como artefactos (HU-33).

Especificación: specs/034-hu-33-prompts-versionados/spec.md
- RF-1: los prompts se guardan como archivos versionados con id y hash de contenido.
- RF-2: el pipeline carga el prompt desde esos archivos, no desde una cadena inline.
- RF-5: CI falla si el contenido de un prompt cambia sin cambiar su versión.

`prompts/manifest.toml` es la única fuente de verdad de las versiones: una entrada
por versión con `id`, `version`, `archivo`, `sha256`, `descripcion` y `vigente`.
Este módulo es el único cargador: nada más lee archivos de `prompts/`. El contrato
`Prompt` está congelado en `specs/034-hu-33-prompts-versionados/plan.md` porque
HU-35 (edición iterativa) y SPEC-053 (A/B) lo consumen.

Solo biblioteca estándar (`hashlib`, `tomllib`, `dataclasses`, `pathlib`): sin red,
sin GPU y sin dependencias nuevas.
"""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

#: Id del prompt que usa el pipeline hoy; HU-35 pedirá el mismo id con otra versión.
PROMPT_VIGENTE = "planner"
#: Raíz por defecto de los artefactos de prompt (`prompts/` en la raíz del repo).
RUTA_PROMPTS = Path(__file__).resolve().parents[2] / "prompts"
MANIFIESTO = "manifest.toml"
LONGITUD_SHA256 = 64

#: Claves obligatorias de cada entrada del manifiesto.
_CLAVES = ("id", "version", "archivo", "sha256", "descripcion", "vigente")
_HEXADECIMAL = frozenset("0123456789abcdef")


class ErrorPrompt(ValueError):
    """El prompt no existe, está mal declarado o su hash no coincide con el archivo."""


@dataclass(frozen=True)
class Prompt:
    """Versión cargada de un prompt: identidad, procedencia y texto exacto."""

    id: str
    version: int
    archivo: str
    sha256: str
    texto: str

    @property
    def etiqueta(self) -> str:
        """Versión de prompt en un solo token (`planner-v1`), la que viaja al registro."""
        return f"{self.id}-v{self.version}"


def sha256_texto(texto: str) -> str:
    """SHA-256 hexadecimal del texto cargado (archivo menos su salto final)."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _raiz(raiz: Path | None) -> Path:
    return Path(raiz) if raiz is not None else RUTA_PROMPTS


def cargar_manifiesto(*, raiz: Path | None = None) -> dict:
    """Lee y decodifica `manifest.toml`; `ErrorPrompt` si falta o no es TOML válido."""
    ruta = _raiz(raiz) / MANIFIESTO
    try:
        return tomllib.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ErrorPrompt(f"No se encontró el manifiesto de prompts: {ruta}.") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ErrorPrompt(f"El manifiesto de prompts no es TOML válido ({ruta}): {exc}.") from exc


def _entradas(manifiesto: dict, raiz: Path) -> list[dict]:
    """Lista de entradas `[[prompts]]` del manifiesto; tolera un manifiesto vacío."""
    entradas = manifiesto.get("prompts", [])
    if not isinstance(entradas, list) or any(not isinstance(e, dict) for e in entradas):
        raise ErrorPrompt(
            f"El manifiesto de prompts no declara una lista [[prompts]] válida en {raiz}."
        )
    return entradas


def _texto_cargado(ruta: Path) -> str:
    """Contenido del archivo menos exactamente un salto de línea final."""
    contenido = ruta.read_text(encoding="utf-8")
    return contenido[:-1] if contenido.endswith("\n") else contenido


def _sha256_valido(valor: object) -> bool:
    if not isinstance(valor, str):
        return False
    return len(valor) == LONGITUD_SHA256 and set(valor) <= _HEXADECIMAL


def _mensaje_hash(entrada: dict, calculado: str) -> str:
    """Error de integridad: archivo, versión declarada y los dos hashes (AC2)."""
    return (
        f"{entrada['archivo']}: la versión {entrada['version']} declara sha256 "
        f"{entrada['sha256']} pero el contenido da {calculado}; si cambiaste el texto, "
        "crea un archivo nuevo y sube `version`."
    )


def _validar_entrada(entrada: dict, raiz: Path) -> None:
    """Una entrada del manifiesto tiene que declarar todas sus claves."""
    faltan = [clave for clave in _CLAVES if clave not in entrada]
    if faltan:
        raise ErrorPrompt(
            f"Entrada del manifiesto incompleta en {raiz / MANIFIESTO}: falta «{faltan[0]}»."
        )


def _prompt_de(entrada: dict, raiz: Path) -> Prompt:
    """Carga una entrada concreta y verifica su hash contra el archivo declarado."""
    _validar_entrada(entrada, raiz)
    archivo = str(entrada["archivo"])
    ruta = raiz / archivo
    try:
        texto = _texto_cargado(ruta)
    except FileNotFoundError as exc:
        raise ErrorPrompt(
            f"{ruta}: la versión {entrada['version']} apunta a un archivo que no existe."
        ) from exc
    calculado = sha256_texto(texto)
    if calculado != str(entrada["sha256"]):
        raise ErrorPrompt(_mensaje_hash(entrada, calculado))
    return Prompt(
        id=str(entrada["id"]),
        version=int(entrada["version"]),
        archivo=archivo,
        sha256=str(entrada["sha256"]),
        texto=texto,
    )


def cargar(id_prompt: str = PROMPT_VIGENTE, *, raiz: Path | None = None) -> Prompt:
    """Carga la versión vigente del prompt `id_prompt` y valida su hash (RF-1, RF-2).

    Lanza `ErrorPrompt` si el manifiesto falta, si el id no existe, si no hay
    exactamente una versión vigente o si el contenido no coincide con el `sha256`
    declarado.
    """
    base = _raiz(raiz)
    entradas = _entradas(cargar_manifiesto(raiz=base), base)
    vigentes = [
        entrada
        for entrada in entradas
        if entrada.get("id") == id_prompt and entrada.get("vigente") is True
    ]
    if not vigentes:
        raise ErrorPrompt(
            f"El manifiesto de prompts no declara una versión vigente para «{id_prompt}» "
            f"({base / MANIFIESTO})."
        )
    if len(vigentes) > 1:
        versiones = ", ".join(str(entrada.get("version")) for entrada in vigentes)
        raise ErrorPrompt(
            f"El manifiesto de prompts declara más de una versión vigente para "
            f"«{id_prompt}»: {versiones}."
        )
    return _prompt_de(vigentes[0], base)


def listar(*, raiz: Path | None = None) -> list[Prompt]:
    """Carga todas las entradas del manifiesto, vigentes o no, con su hash validado."""
    base = _raiz(raiz)
    entradas = _entradas(cargar_manifiesto(raiz=base), base)
    return [_prompt_de(entrada, base) for entrada in entradas]


def verificar(*, raiz: Path | None = None) -> list[str]:
    """Errores de integridad del manifiesto; lista vacía significa consistente (RF-5).

    Nunca lanza por un problema del manifiesto: los acumula como mensajes en
    español para que el chequeo de CI los imprima todos de una vez.
    """
    base = _raiz(raiz)
    try:
        entradas = _entradas(cargar_manifiesto(raiz=base), base)
    except ErrorPrompt as exc:
        return [str(exc)]

    errores: list[str] = []
    vistas: set[tuple[str, object]] = set()
    vigentes: dict[str, int] = {}
    for entrada in entradas:
        faltan = [clave for clave in _CLAVES if clave not in entrada]
        if faltan:
            errores.append(
                f"Entrada del manifiesto incompleta en {base / MANIFIESTO}: falta «{faltan[0]}»."
            )
            continue
        id_prompt = str(entrada["id"])
        version = entrada["version"]
        archivo = str(entrada["archivo"])
        declarado = entrada["sha256"]
        vigentes.setdefault(id_prompt, 0)
        if (id_prompt, version) in vistas:
            errores.append(
                f"El prompt {id_prompt} declara la versión {version} duplicada ({archivo})."
            )
        vistas.add((id_prompt, version))
        if entrada["vigente"] is True:
            vigentes[id_prompt] = vigentes.get(id_prompt, 0) + 1
        if not _sha256_valido(declarado):
            errores.append(
                f"{archivo}: la versión {version} declara un sha256 con formato inválido "
                f"({declarado}); se esperan {LONGITUD_SHA256} caracteres hexadecimales "
                "en minúscula."
            )
        ruta = base / archivo
        if not ruta.is_file():
            errores.append(f"{ruta}: la versión {version} apunta a un archivo que no existe.")
            continue
        if _sha256_valido(declarado):
            calculado = sha256_texto(_texto_cargado(ruta))
            if calculado != declarado:
                errores.append(_mensaje_hash(entrada, calculado))
    for id_prompt, cuenta in sorted(vigentes.items()):
        if cuenta != 1:
            errores.append(
                f"El prompt {id_prompt} declara {cuenta} versiones vigentes; debe declarar "
                "exactamente una."
            )
    return errores
