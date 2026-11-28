"""Catálogo y plantillas guardadas de piezas (SPEC-050, HU-49).

Especificación: specs/050-hu-49-plantillas-parametrizadas/spec.md
- RF-1: catálogo de plantillas con tipo, parámetros, unidad, defecto y rango.
- RF-2: instanciar produce un programa DSL que pasa la misma verificación que el flujo
  por texto; este módulo no construye, solo arma el programa (el pipeline lo verifica).
- RF-3: una pieza generada puede guardarse como plantilla reutilizando su programa.
- RF-4: un parámetro fuera de rango se rechaza antes de construir, nombrando el
  parámetro y su rango.
- RNF-3: el catálogo es un archivo de datos versionado (`data/plantillas.toml`); las
  plantillas guardadas viven en `data/plantillas.json` (fuera de Git) con su propietario.

Solo biblioteca estándar y lectura local: sin red, sin GPU y sin dependencias nuevas.
"""

from __future__ import annotations

import json
import os
import re
import tomllib
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from m2_cad import materiales
from m2_cad.persistencia_registro import _bloqueo, _publicar_bytes

#: Raíz del repositorio (`src/m2_cad/` → tres niveles arriba).
RAIZ = Path(__file__).resolve().parents[2]
#: Catálogo versionado de plantillas (se revisa en el PR, no se genera).
RUTA_CATALOGO = RAIZ / "data" / "plantillas.toml"
#: Índice de plantillas guardadas por los usuarios (fuera de Git).
RUTA_GUARDADAS = RAIZ / "data" / "plantillas.json"
VARIABLE_CATALOGO = "M2_PLANTILLAS"
VARIABLE_GUARDADAS = "M2_PLANTILLAS_JSON"

VERSION = 1
UNIDADES = ("mm", "u")
#: Parámetros que son cuentas y no medidas.
CONTADORES = frozenset({"bolt_count"})
#: Familias del banco (`src/m2_cad/dataset.py`), incluida la etiqueta del tornillo.
FAMILIAS = ("plate", "sheet_bracket", "adapter", "flange", "spacer", "tornillería")
#: Tipo del motor → familia del banco (el tornillo es `screw` y `tornillería`).
FAMILIA_DEL_TIPO = {
    "plate": "plate",
    "sheet_bracket": "sheet_bracket",
    "adapter": "adapter",
    "flange": "flange",
    "spacer": "spacer",
    "screw": "tornillería",
}
_MARGEN_RANGO = 0.5
_PLANTILLA_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")


class ErrorPlantilla(RuntimeError):
    """La plantilla no existe, no es del usuario o el catálogo está mal declarado."""


class ErrorParametro(ValueError):
    """Un parámetro pedido no existe, no es numérico o está fuera de su rango (RF-4)."""


def ruta_catalogo() -> Path:
    """Ruta efectiva del catálogo: `M2_PLANTILLAS` si está definida, si no la versionada."""
    configurada = os.environ.get(VARIABLE_CATALOGO, "").strip()
    return Path(configurada) if configurada else RUTA_CATALOGO


def ruta_guardadas() -> Path:
    """Ruta efectiva del índice de plantillas guardadas (`M2_PLANTILLAS_JSON`)."""
    configurada = os.environ.get(VARIABLE_GUARDADAS, "").strip()
    return Path(configurada) if configurada else RUTA_GUARDADAS


def _leer_catalogo(destino: Path | None = None) -> dict[str, Any]:
    archivo = Path(destino) if destino is not None else ruta_catalogo()
    try:
        texto = archivo.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ErrorPlantilla(f"no existe el catálogo de plantillas: {archivo}") from exc
    except OSError as exc:
        raise ErrorPlantilla(f"no se pudo leer el catálogo de plantillas: {archivo}") from exc
    try:
        datos = tomllib.loads(texto)
    except tomllib.TOMLDecodeError as exc:
        raise ErrorPlantilla(f"el catálogo de plantillas no es TOML válido: {archivo}") from exc
    if not isinstance(datos.get("plantillas"), list):
        raise ErrorPlantilla(f"el catálogo no declara entradas [[plantillas]]: {archivo}")
    return datos


def cargar_catalogo(destino: Path | None = None) -> dict[str, dict[str, Any]]:
    """Plantillas del catálogo por id, sin tocar las guardadas por los usuarios."""
    catalogo: dict[str, dict[str, Any]] = {}
    for entrada in _leer_catalogo(destino)["plantillas"]:
        if isinstance(entrada, dict) and str(entrada.get("id", "")).strip():
            catalogo[str(entrada["id"])] = entrada
    return catalogo


def _tipo_de_la_parte(programa: Any) -> dict[str, Any]:
    """La única parte del programa plantilla, o error si no es una pieza simple."""
    if not isinstance(programa, dict):
        raise ErrorPlantilla("el programa de la plantilla no es un objeto")
    partes = programa.get("parts")
    if not isinstance(partes, list) or len(partes) != 1 or not isinstance(partes[0], dict):
        raise ErrorPlantilla("la plantilla debe describir exactamente una pieza")
    return partes[0]


def _tipos_del_motor() -> dict[str, str]:
    """Tipos del motor, si el entorno del proyecto está disponible (patrón HU-48).

    `pipeline` arrastra el núcleo CAD, así que la puerta de CI no puede importarlo:
    ahí se valida contra los tipos que declara este módulo, y `make check` (con el
    entorno completo) valida además que no se hayan despegado del pipeline.
    """
    try:
        from m2_cad.pipeline import CATALOGO
    except ImportError:  # pragma: no cover - depende del entorno de ejecución
        return {tipo: tipo for tipo in FAMILIA_DEL_TIPO}
    return CATALOGO


def verificar(destino: Path | None = None) -> list[str]:
    """Problemas del catálogo, en español; lista vacía si es válido (RF-1, RNF-3)."""
    archivo = Path(destino) if destino is not None else ruta_catalogo()
    try:
        datos = _leer_catalogo(archivo)
    except ErrorPlantilla as exc:
        return [str(exc)]

    catalogo_tipos = _tipos_del_motor()

    problemas: list[str] = []
    if datos.get("version") != VERSION:
        problemas.append(f"el catálogo de plantillas debe declarar version = {VERSION}")
    vistos: set[str] = set()
    tipos: set[str] = set()
    for entrada in datos["plantillas"]:
        if not isinstance(entrada, dict):
            problemas.append("cada entrada del catálogo debe ser una tabla")
            continue
        identificador = str(entrada.get("id", "")).strip()
        if not _PLANTILLA_ID.match(identificador):
            problemas.append(f"el id «{identificador}» debe ser un slug en minúsculas")
            continue
        if identificador in vistos:
            problemas.append(f"el id «{identificador}» está repetido en el catálogo")
        vistos.add(identificador)
        if not str(entrada.get("nombre", "")).strip():
            problemas.append(f"la plantilla «{identificador}» no declara nombre")
        tipo = str(entrada.get("tipo", "")).strip()
        tipos.add(tipo)
        if tipo not in catalogo_tipos:
            problemas.append(f"la plantilla «{identificador}» usa un tipo desconocido: {tipo}")
        familia = str(entrada.get("familia", "")).strip()
        if familia not in FAMILIAS:
            problemas.append(
                f"la plantilla «{identificador}» usa una familia desconocida: {familia}"
            )
        elif FAMILIA_DEL_TIPO.get(tipo) != familia:
            problemas.append(
                f"la plantilla «{identificador}» declara familia «{familia}» para el tipo «{tipo}»"
            )
        try:
            parte = _tipo_de_la_parte(entrada.get("programa"))
        except ErrorPlantilla as exc:
            problemas.append(f"la plantilla «{identificador}»: {exc}")
            continue
        if parte.get("type") != tipo:
            problemas.append(
                f"la plantilla «{identificador}»: el programa no es del tipo declarado"
            )
        material = str(parte.get("material", "")).strip()
        if materiales.normalizar(material) is None:
            problemas.append(
                f"la plantilla «{identificador}» usa un material no soportado: {material}"
            )
        parametros = entrada.get("parametros")
        if not isinstance(parametros, list) or not parametros:
            problemas.append(f"la plantilla «{identificador}» no declara parámetros")
            continue
        params = parte.get("params") if isinstance(parte.get("params"), dict) else {}
        for parametro in parametros:
            problemas.extend(_verificar_parametro(identificador, parametro, params))
    for familia in FAMILIAS:
        if FAMILIA_DEL_TIPO and familia not in {
            FAMILIA_DEL_TIPO[tipo] for tipo in tipos if tipo in FAMILIA_DEL_TIPO
        }:
            problemas.append(f"falta la plantilla de la familia «{familia}»")
    return problemas


def _verificar_parametro(identificador: str, parametro: Any, params: dict[str, Any]) -> list[str]:
    problemas: list[str] = []
    if not isinstance(parametro, dict):
        return [f"la plantilla «{identificador}» declara un parámetro que no es una tabla"]
    nombre = str(parametro.get("nombre", "")).strip()
    etiqueta = f"la plantilla «{identificador}», parámetro «{nombre}»"
    if not nombre:
        return [f"la plantilla «{identificador}» declara un parámetro sin nombre"]
    if nombre not in params:
        problemas.append(f"{etiqueta}: no existe en el programa de la plantilla")
    if not str(parametro.get("etiqueta", "")).strip():
        problemas.append(f"{etiqueta}: no declara etiqueta")
    if parametro.get("unidad") not in UNIDADES:
        problemas.append(f"{etiqueta}: la unidad debe ser una de {list(UNIDADES)}")
    valores: dict[str, float] = {}
    for clave in ("defecto", "minimo", "maximo"):
        valor = parametro.get(clave)
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            problemas.append(f"{etiqueta}: «{clave}» debe ser numérico")
            continue
        valores[clave] = float(valor)
    if len(valores) == 3:
        if valores["minimo"] >= valores["maximo"]:
            problemas.append(f"{etiqueta}: el mínimo debe ser menor que el máximo")
        elif not valores["minimo"] <= valores["defecto"] <= valores["maximo"]:
            problemas.append(f"{etiqueta}: el valor por defecto debe estar dentro del rango")
    permitidos = parametro.get("valores")
    if permitidos is not None:
        if (
            not isinstance(permitidos, list)
            or not permitidos
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in permitidos)
        ):
            problemas.append(f"{etiqueta}: «valores» debe ser una lista de números")
        elif len(valores) == 3 and (
            valores["defecto"] not in permitidos
            or any(not valores["minimo"] <= v <= valores["maximo"] for v in permitidos)
        ):
            problemas.append(
                f"{etiqueta}: el defecto y los «valores» permitidos deben estar dentro del rango"
            )
    return problemas


def parametros_de(plantilla: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Parámetros ajustables de una plantilla, por nombre."""
    return {
        str(parametro["nombre"]): parametro
        for parametro in plantilla.get("parametros") or []
        if isinstance(parametro, dict) and str(parametro.get("nombre", "")).strip()
    }


def _valor_valido(nombre: str, especificacion: dict[str, Any], crudo: Any) -> int | float:
    """Convierte y valida un valor contra su rango; el mensaje nombra parámetro y rango (RF-4)."""
    etiqueta = str(especificacion.get("etiqueta") or nombre)
    unidad = str(especificacion.get("unidad") or "mm")
    if isinstance(crudo, bool) or not isinstance(crudo, (int, float)):
        raise ErrorParametro(
            f"el parámetro «{nombre}» ({etiqueta}) debe ser un número en {unidad}; recibí {crudo!r}"
        )
    try:
        valor = float(crudo)
    except OverflowError as exc:
        raise ErrorParametro(
            f"el parámetro «{nombre}» ({etiqueta}) está fuera de cualquier rango válido"
        ) from exc
    if especificacion.get("entero") and not valor.is_integer():
        raise ErrorParametro(
            f"el parámetro «{nombre}» ({etiqueta}) debe ser un entero; recibí {crudo:g}"
        )
    minimo = float(especificacion["minimo"])
    maximo = float(especificacion["maximo"])
    if not minimo <= valor <= maximo:
        raise ErrorParametro(
            f"el parámetro «{nombre}» ({etiqueta}) debe estar entre {minimo:g} y {maximo:g} "
            f"{unidad}; recibí {valor:g}"
        )
    permitidos = especificacion.get("valores")
    if permitidos and valor not in [float(v) for v in permitidos]:
        raise ErrorParametro(
            f"el parámetro «{nombre}» ({etiqueta}) debe ser uno de "
            f"{', '.join(f'{float(v):g}' for v in permitidos)} {unidad}; recibí {valor:g}"
        )
    return int(valor) if especificacion.get("entero") else valor


def instanciar(plantilla: dict[str, Any], valores: dict[str, Any] | None = None) -> dict[str, Any]:
    """Programa DSL de la plantilla con los valores pedidos (RF-2, RF-4, RNF-1).

    No construye ni consulta al modelo: devuelve el programa que el pipeline verifica
    igual que el de una generación por texto.
    """
    pedidos = dict(valores or {})
    conocidos = parametros_de(plantilla)
    ajenos = sorted(set(pedidos) - set(conocidos))
    if ajenos:
        raise ErrorParametro(
            f"el parámetro «{ajenos[0]}» no existe en la plantilla «{plantilla.get('nombre')}»; "
            f"disponibles: {', '.join(sorted(conocidos))}"
        )
    programa = deepcopy(plantilla["programa"])
    params = _tipo_de_la_parte(programa).setdefault("params", {})
    for nombre, especificacion in conocidos.items():
        crudo = pedidos.get(nombre, especificacion["defecto"])
        params[nombre] = _valor_valido(nombre, especificacion, crudo)
    return programa


def derivar_parametros(programa: dict[str, Any]) -> list[dict[str, Any]]:
    """Parámetros ajustables derivados de una pieza, con rango ±50 % (RF-3).

    Expone los `params` numéricos con valor positivo. Las medidas van en mm con un rango
    de ±50 %; las cuentas (`CONTADORES`) son enteras, con mínimo 1 y máximo el doble.
    Los textos, booleanos y funciones apagadas (valor 0) quedan fijos en el programa. El
    valor por defecto es el original sin redondear, así que instanciar sin cambios
    reproduce la misma pieza (AC3).
    """
    parte = _tipo_de_la_parte(programa)
    params = parte.get("params")
    discretos = _parametros_discretos(str(parte.get("type", "")))
    derivados: list[dict[str, Any]] = []
    for nombre, valor in (params or {}).items():
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor <= 0:
            continue
        if nombre in discretos and valor in discretos[nombre]["valores"]:
            # Un valor discreto (p. ej. la clase ASME de una brida) hereda la lista
            # permitida del catálogo: un ±50 % aceptaría valores que el núcleo rechaza.
            derivados.append({**discretos[nombre], "defecto": valor})
            continue
        contador = nombre in CONTADORES
        if contador:
            minimo: int | float = max(1, int(valor * (1 - _MARGEN_RANGO)))
            maximo: int | float = int(valor) * 2
        else:
            minimo = round(valor * (1 - _MARGEN_RANGO), 3)
            maximo = round(valor * (1 + _MARGEN_RANGO), 3)
        derivados.append(
            {
                "nombre": str(nombre),
                "etiqueta": str(nombre),
                "unidad": "u" if contador else "mm",
                "defecto": int(valor) if contador else valor,
                "minimo": minimo,
                "maximo": maximo,
                "entero": contador,
            }
        )
    return derivados


def _parametros_discretos(tipo: str) -> dict[str, dict[str, Any]]:
    """Parámetros con `valores` permitidos que declara el catálogo para ese tipo."""
    try:
        catalogo = cargar_catalogo()
    except ErrorPlantilla:
        return {}
    return {
        nombre: deepcopy(especificacion)
        for plantilla in catalogo.values()
        if plantilla.get("tipo") == tipo
        for nombre, especificacion in parametros_de(plantilla).items()
        if especificacion.get("valores")
    }


def _leer_indice(destino: Path) -> dict[str, Any]:
    try:
        datos = json.loads(destino.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": VERSION, "plantillas": []}
    except (OSError, json.JSONDecodeError) as exc:
        raise ErrorPlantilla(f"el índice de plantillas no se pudo leer: {destino}") from exc
    if not isinstance(datos, dict) or not isinstance(datos.get("plantillas"), list):
        raise ErrorPlantilla(f"el índice de plantillas no tiene la forma esperada: {destino}")
    return datos


def listar_guardadas(usuario: str, destino: Path | None = None) -> list[dict[str, Any]]:
    """Plantillas guardadas por ese usuario, en orden de creación (RF-3)."""
    archivo = Path(destino) if destino is not None else ruta_guardadas()
    return [
        entrada
        for entrada in _leer_indice(archivo)["plantillas"]
        if isinstance(entrada, dict) and entrada.get("usuario") == usuario
    ]


def guardar(
    usuario: str,
    nombre: str,
    programa: dict[str, Any],
    *,
    parametros: list[dict[str, Any]] | None = None,
    destino: Path | None = None,
) -> dict[str, Any]:
    """Guarda el programa de una pieza como plantilla del usuario (RF-3).

    La escritura es atómica y bajo bloqueo: el índice nunca queda a medias y dos
    usuarios no se pisan. El propietario viaja en la entrada, no en la ruta.
    """
    limpio = nombre.strip()
    if not limpio:
        raise ErrorPlantilla("la plantilla necesita un nombre")
    if len(limpio) > 80:
        raise ErrorPlantilla("el nombre de la plantilla no puede superar 80 caracteres")
    parte = _tipo_de_la_parte(programa)
    tipo = str(parte.get("type", ""))
    familia = FAMILIA_DEL_TIPO.get(tipo)
    if familia is None:
        raise ErrorPlantilla(f"la pieza de tipo «{tipo}» no tiene plantilla de catálogo")
    entrada = {
        "id": uuid.uuid4().hex,
        "usuario": usuario,
        "nombre": limpio,
        "descripcion": f"Plantilla guardada desde una pieza de tipo {tipo}.",
        "tipo": tipo,
        "familia": familia,
        "programa": deepcopy(programa),
        "parametros": deepcopy(parametros)
        if parametros is not None
        else derivar_parametros(programa),
        "creada": datetime.now(UTC).isoformat(),
    }
    archivo = Path(destino) if destino is not None else ruta_guardadas()
    archivo.parent.mkdir(parents=True, exist_ok=True)
    with _bloqueo(archivo):
        datos = _leer_indice(archivo)
        datos["version"] = VERSION
        datos["plantillas"].append(entrada)
        _publicar_bytes(archivo, json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8"))
    return entrada


def obtener(plantilla_id: str, usuario: str, destino: Path | None = None) -> dict[str, Any]:
    """Plantilla del catálogo (de todos) o guardada por ese usuario; 404 si es ajena.

    Aislamiento: una plantilla guardada por otro usuario responde igual que una que no
    existe, sin revelar que existe. La comprobación vive acá además de en la API para
    que ningún camino pueda saltársela.
    """
    catalogo = cargar_catalogo()
    if plantilla_id in catalogo:
        return {**catalogo[plantilla_id], "origen": "catalogo"}
    for guardada in listar_guardadas(usuario, destino):
        if guardada.get("id") == plantilla_id:
            return {**guardada, "origen": "guardada"}
    raise ErrorPlantilla("la plantilla no existe.")
