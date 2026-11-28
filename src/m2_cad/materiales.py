"""Tabla versionada de materiales, densidades y precios (SPEC-049, HU-48).

Especificación: specs/049-hu-48-materiales-tolerancias-bom/spec.md
- RF-2: el material canónico viaja explícito al programa DSL y al BOM.
- RF-3: el BOM usa precios por material configurables desde un archivo versionado.
- RF-5: un material fuera del catálogo se declina con un motivo legible.

`data/materiales.toml` es la única fuente de los materiales soportados, de sus alias, de
su densidad (coherente con `DENSITY_G_MM3` del kit) y de su precio. La ruta se puede
cambiar con `M2_MATERIALES`, así que los precios se ajustan sin tocar el código ni
reiniciar el servicio. Solo biblioteca estándar y lectura local: sin red, sin GPU y sin
dependencias nuevas.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

#: Raíz del repositorio (`src/m2_cad/` → tres niveles arriba).
RAIZ = Path(__file__).resolve().parents[2]
#: Tabla versionada de materiales y precios.
RUTA_TABLA = RAIZ / "data" / "materiales.toml"
#: Variable de entorno que permite apuntar a otra tabla (pruebas o despliegue).
VARIABLE_ENTORNO = "M2_MATERIALES"

#: Versión del formato del archivo; cambia si cambia la forma de las entradas.
VERSION = 1
MONEDA = "USD"
UNIDAD_PRECIO = "kg"

#: Materiales canónicos: los mismos que ofrece el planificador
#: (`prompts/planner-v1.txt`). Es el catálogo cerrado que valida el guard de RF-5.
SOPORTADOS = ("steel", "stainless", "aluminum", "brass", "copper", "abs", "pla", "nylon")


class ErrorMateriales(RuntimeError):
    """La tabla no existe, no es TOML válido o no permite calcular un costo."""


def ruta_tabla() -> Path:
    """Ruta efectiva de la tabla: `M2_MATERIALES` si está definida, si no la versionada."""
    configurada = os.environ.get(VARIABLE_ENTORNO, "").strip()
    return Path(configurada) if configurada else RUTA_TABLA


def _leer(destino: Path | None = None) -> dict[str, Any]:
    """Lee y parsea la tabla; un archivo ilegible es error de configuración."""
    archivo = Path(destino) if destino is not None else ruta_tabla()
    try:
        texto = archivo.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ErrorMateriales(f"no existe la tabla de materiales: {archivo}") from exc
    except OSError as exc:
        raise ErrorMateriales(f"no se pudo leer la tabla de materiales: {archivo}") from exc
    try:
        datos = tomllib.loads(texto)
    except tomllib.TOMLDecodeError as exc:
        raise ErrorMateriales(f"la tabla de materiales no es TOML válido: {archivo}") from exc
    if not isinstance(datos.get("materiales"), list):
        raise ErrorMateriales(f"la tabla no declara entradas [[materiales]]: {archivo}")
    return datos


def cargar(destino: Path | None = None) -> dict[str, dict[str, Any]]:
    """Materiales por nombre canónico, con su densidad, precio, alias y procedencia."""
    tabla: dict[str, dict[str, Any]] = {}
    for entrada in _leer(destino)["materiales"]:
        if not isinstance(entrada, dict):
            continue
        nombre = str(entrada.get("nombre", "")).strip().lower()
        if nombre:
            tabla[nombre] = entrada
    return tabla


def normalizar(pedido: object) -> str | None:
    """Nombre canónico del material pedido, o `None` si no está soportado (RF-2, RF-5).

    Acepta mayúsculas, espacios y los alias declarados en la tabla (`al` → `aluminum`).
    No inventa material: lo que no está en el catálogo devuelve `None` para que el
    guard decline con un motivo que nombre lo pedido.
    """
    if not isinstance(pedido, str):
        return None
    texto = pedido.strip().lower()
    if not texto:
        return None
    if texto in SOPORTADOS:
        return texto
    for nombre, entrada in cargar().items():
        alias = entrada.get("alias") or []
        if isinstance(alias, list) and any(
            isinstance(item, str) and item.strip().lower() == texto for item in alias
        ):
            return nombre
    return None


def precio_usd_g(material: object) -> float:
    """Precio por gramo del material, en la moneda de la tabla (RF-3).

    Un material sin precio en la tabla no se estima: es un error de configuración que
    nombra el material, para que nadie publique un costo inventado.
    """
    canonico = normalizar(material)
    if canonico is None:
        raise ErrorMateriales(f"«{material}» no es un material de la tabla de precios")
    entrada = cargar().get(canonico, {})
    precio = entrada.get("precio_usd_kg")
    if isinstance(precio, bool) or not isinstance(precio, (int, float)) or precio <= 0:
        raise ErrorMateriales(f"el material «{canonico}» no tiene un precio_usd_kg positivo")
    return float(precio) / 1000


def _densidades_del_kit() -> dict[str, float]:
    """Densidades del kit vendoreado, si el entorno del proyecto está disponible.

    La puerta de CI corre sin instalar el proyecto, así que la comparación con el kit es
    opcional allí; donde el kit existe (`make check`), detecta cualquier divergencia.
    """
    try:
        from constraint_kit.parts import DENSITY_G_MM3
    except ImportError:  # pragma: no cover - depende del entorno de ejecución
        return {}
    return dict(DENSITY_G_MM3)


def verificar(destino: Path | None = None) -> list[str]:
    """Problemas de la tabla, en español; lista vacía si es válida (RF-3).

    Comprueba la versión, la moneda y la unidad del precio, que estén los materiales
    canónicos y ninguno de más, que cada uno tenga densidad y precio positivos y que los
    alias no choquen entre sí ni con un nombre canónico.
    """
    archivo = Path(destino) if destino is not None else ruta_tabla()
    try:
        datos = _leer(archivo)
    except ErrorMateriales as exc:
        return [str(exc)]

    problemas: list[str] = []
    if datos.get("version") != VERSION:
        problemas.append(f"la tabla de materiales debe declarar version = {VERSION}")
    if datos.get("moneda") != MONEDA:
        problemas.append(f"la tabla de materiales debe declarar moneda = {MONEDA!r}")
    if datos.get("unidad_precio") != UNIDAD_PRECIO:
        problemas.append(f"la tabla de materiales debe declarar unidad_precio = {UNIDAD_PRECIO!r}")

    tabla = cargar(archivo)
    for nombre in SOPORTADOS:
        if nombre not in tabla:
            problemas.append(f"falta el material «{nombre}» en la tabla de materiales")
    for nombre in sorted(set(tabla) - set(SOPORTADOS)):
        problemas.append(f"el material «{nombre}» no está en el catálogo del planificador")

    densidades = _densidades_del_kit()
    alias_vistos: dict[str, str] = {}
    for nombre in SOPORTADOS:
        entrada = tabla.get(nombre)
        if entrada is None:
            continue
        densidad = entrada.get("densidad_g_mm3")
        if isinstance(densidad, bool) or not isinstance(densidad, (int, float)) or densidad <= 0:
            problemas.append(f"la densidad de «{nombre}» debe ser un número positivo")
        elif nombre in densidades and densidad != densidades[nombre]:
            problemas.append(
                f"la densidad de «{nombre}» ({densidad}) no coincide con DENSITY_G_MM3 "
                f"({densidades[nombre]})"
            )
        precio = entrada.get("precio_usd_kg")
        if isinstance(precio, bool) or not isinstance(precio, (int, float)) or precio <= 0:
            problemas.append(f"el precio de «{nombre}» debe ser un número positivo")
        alias = entrada.get("alias") or []
        if not isinstance(alias, list):
            problemas.append(f"los alias de «{nombre}» deben ser una lista")
            continue
        for item in alias:
            if not isinstance(item, str) or not item.strip():
                problemas.append(f"el alias de «{nombre}» debe ser texto no vacío")
                continue
            clave = item.strip().lower()
            if clave in SOPORTADOS:
                problemas.append(f"el alias «{clave}» de «{nombre}» choca con un material canónico")
            elif clave in alias_vistos:
                problemas.append(
                    f"el alias «{clave}» de «{nombre}» ya lo declara «{alias_vistos[clave]}»"
                )
            else:
                alias_vistos[clave] = nombre
    return problemas
