"""Corpus dorado del núcleo determinista (HU-23, SPEC-024).

Un corpus versionado de pares *programa DSL → resultado congelado* (`acepta` con la
huella del STEP, o `declina`) que se compara en CI contra lo que el núcleo produce
hoy. Una divergencia geométrica del núcleo, incluso por debajo de la tolerancia de
±2 % que compara `tests/test_pipeline.py`, cambia el STEP y por tanto la huella.

El módulo no importa `constraint_kit` al cargarse: el verificador y el constructor
se importan sólo al construir cada caso, para que el esquema del corpus se pueda
validar sin el kernel CAD instalado.
"""

import copy
import hashlib
import json
import re
import tempfile
from pathlib import Path

from m2_cad import dataset

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "corpus_dorado.json"
VERSION = 1
RESULTADOS = ("acepta", "declina")
CLAVES_CASO = ("id", "fuente", "programa", "resultado", "sha256")
HEXADECIMAL = re.compile(r"[0-9a-f]{64}")

# Sólo lo que cambia entre dos corridas del mismo programa, medido en `plan.md` §1.1.
# Cualquier divergencia real del núcleo toca el resto del archivo y cambia la huella.
_GUID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_MARCA_TIEMPO = re.compile(r"(FILE_NAME\(\s*'[^']*'\s*,\s*)'[^']*'")
_OCURRENCIA = re.compile(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\(\s*'[^']*'")


class ErrorCorpus(ValueError):
    """El corpus está mal definido o un caso no se puede congelar."""


def normalizar_step(texto: str) -> str:
    """Neutraliza los tres campos que varían entre corridas del mismo programa.

    La marca de tiempo de `FILE_NAME`, los GUID que OpenCascade asigna a cada
    `PRODUCT` y el contador de `NEXT_ASSEMBLY_USAGE_OCCURRENCE` (que avanza por
    cada ensamblaje construido en el proceso) no son geometría.
    """
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = _MARCA_TIEMPO.sub(r"\1'<marca-tiempo>'", texto)
    texto = _GUID.sub("<guid>", texto)
    return _OCURRENCIA.sub("NEXT_ASSEMBLY_USAGE_OCCURRENCE('<ocurrencia>'", texto)


def huella_step(ruta: Path) -> str:
    """sha256 del STEP normalizado: la huella congelada en el corpus."""
    texto = normalizar_step(Path(ruta).read_text(encoding="ascii"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _fila_del_banco(identificador: str) -> dict:
    """Fila del banco HU-02 citada por un caso; el banco es la fuente de los parámetros."""
    for fila in dataset.read_dataset():
        if fila["id"] == identificador:
            return fila
    raise ErrorCorpus(f"la fila «{identificador}» no existe en el banco HU-02")


def programa_de_caso(caso: dict) -> dict:
    """Programa DSL del caso: explícito, o derivado de la fila del banco que cita."""
    if "programa" in caso:
        return copy.deepcopy(caso["programa"])
    medidas = json.loads(_fila_del_banco(caso["fuente"])["medidas"])
    if "tipo_motor" not in medidas:
        raise ErrorCorpus(
            f"la fila «{caso['fuente']}» del banco no tiene programa: declara «programa» explícito"
        )
    return {
        "parts": [
            {
                "id": "p",
                "type": medidas["tipo_motor"],
                "material": "steel",
                "params": medidas["parametros"],
            }
        ],
        "mates": [],
    }


def _validar_caso(caso: dict, vistos: set[str], estricto: bool) -> None:
    """Aplica el esquema del corpus: un caso sin resultado declarado es un error."""
    if not isinstance(caso, dict):
        raise ErrorCorpus("cada caso del corpus tiene que ser un objeto JSON")
    ajenas = sorted(set(caso) - set(CLAVES_CASO))
    if ajenas:
        raise ErrorCorpus(f"claves no reconocidas en el caso: {', '.join(ajenas)}")
    identificador = caso.get("id")
    if not isinstance(identificador, str) or not identificador.strip():
        raise ErrorCorpus("cada caso necesita un id no vacío")
    if identificador in vistos:
        raise ErrorCorpus(f"el id «{identificador}» está repetido")
    vistos.add(identificador)
    resultado = caso.get("resultado")
    if resultado is None:
        raise ErrorCorpus(
            f"el caso «{identificador}» no declara resultado: un caso sin resultado no es aceptado"
        )
    if resultado not in RESULTADOS:
        raise ErrorCorpus(
            f"el caso «{identificador}» declara resultado «{resultado}»; "
            f"sólo se admite {', '.join(RESULTADOS)}"
        )
    tiene_fuente = "fuente" in caso
    tiene_programa = "programa" in caso
    if tiene_fuente == tiene_programa:
        raise ErrorCorpus(
            f"el caso «{identificador}» necesita «fuente» (fila del banco) o «programa», "
            "nunca los dos ni ninguno"
        )
    if tiene_fuente and not isinstance(caso["fuente"], str):
        raise ErrorCorpus(f"el caso «{identificador}» tiene una fuente que no es texto")
    if tiene_programa and not isinstance(caso["programa"], dict):
        raise ErrorCorpus(f"el programa del caso «{identificador}» tiene que ser un objeto JSON")
    sha256 = caso.get("sha256")
    if resultado == "acepta" and estricto:
        if not isinstance(sha256, str) or not HEXADECIMAL.fullmatch(sha256):
            raise ErrorCorpus(
                f"el caso «{identificador}» acepta y necesita una huella sha256 hexadecimal de 64"
            )
    elif resultado == "declina" and sha256 is not None and estricto:
        raise ErrorCorpus(
            f"el caso «{identificador}» declina: no puede congelar una huella de STEP"
        )
    if tiene_fuente:
        _fila_del_banco(caso["fuente"])
    else:
        programa = caso["programa"]
        if not programa:
            raise ErrorCorpus(f"el programa del caso «{identificador}» está vacío")


def cargar_corpus(ruta: Path = DEFAULT_PATH, *, estricto: bool = True) -> list[dict]:
    """Lee y valida el corpus; devuelve los casos.

    En modo `estricto` exige la huella de cada caso aceptado (lo que se congela).
    En modo de regeneración (`estricto=False`) basta el resultado declarado: un
    caso nuevo se agrega con `id`, `fuente` o `programa`, y `resultado`, y la
    huella se congela después con `--write` (RF-5).
    """
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ErrorCorpus("el corpus tiene que ser un objeto JSON")
    if datos.get("version") != VERSION:
        raise ErrorCorpus(f"el corpus necesita version = {VERSION}")
    casos = datos.get("casos")
    if not isinstance(casos, list) or not casos:
        raise ErrorCorpus("el corpus necesita una lista «casos» no vacía")
    vistos: set[str] = set()
    for caso in casos:
        _validar_caso(caso, vistos, estricto)
    return casos


def observar(caso: dict, directorio: Path) -> dict:
    """Construye el caso y devuelve lo observado: declinación o huella del STEP."""
    from m2_cad import pipeline

    try:
        pieza = pipeline.construir_pieza(programa_de_caso(caso), directorio)
    except pipeline.PiezaDeclinada:
        return {"resultado": "declina"}
    except pipeline.ErrorVerificacion as error:
        raise ErrorCorpus(
            f"el caso «{caso['id']}» no verifica: {error}; un programa inválido no se congela"
        ) from error
    return {"resultado": "acepta", "sha256": huella_step(pieza.step)}


def congelado(caso: dict) -> dict:
    """Resultado declarado en el corpus, sin campos de gestión."""
    observado = {"resultado": caso["resultado"]}
    if caso["resultado"] == "acepta":
        observado["sha256"] = caso["sha256"]
    return observado


def comparar(casos: list[dict], directorio: Path) -> list[dict]:
    """Compara cada caso con lo congelado y devuelve las divergencias."""
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    divergencias = []
    for caso in casos:
        with tempfile.TemporaryDirectory(prefix=f"{caso['id']}-", dir=directorio) as temporal:
            observado = observar(caso, Path(temporal))
        esperado = congelado(caso)
        if observado == esperado:
            continue
        divergencias.append({"id": caso["id"], "esperado": esperado, "obtenido": observado})
    return divergencias


def describir(divergencia: dict) -> str:
    """Línea legible con el caso, lo esperado y lo obtenido (AC1 y AC2)."""
    esperado = divergencia["esperado"]
    obtenido = divergencia["obtenido"]
    if esperado["resultado"] != obtenido["resultado"]:
        return (
            f"«{divergencia['id']}»: se esperaba {esperado['resultado']} y el núcleo "
            f"devolvió {obtenido['resultado']}"
        )
    return (
        f"«{divergencia['id']}»: huella del STEP distinta; "
        f"esperada {esperado['sha256']}, obtenida {obtenido['sha256']}"
    )


def regenerar(casos: list[dict], directorio: Path) -> list[dict]:
    """Vuelve a construir cada caso y devuelve lo observado, listo para congelar (RF-5)."""
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    regenerados = []
    for caso in casos:
        with tempfile.TemporaryDirectory(prefix=f"{caso['id']}-", dir=directorio) as temporal:
            observado = observar(caso, Path(temporal))
        regenerado = {"id": caso["id"]}
        if "fuente" in caso:
            regenerado["fuente"] = caso["fuente"]
        if "programa" in caso:
            regenerado["programa"] = caso["programa"]
        regenerado.update(observado)
        regenerados.append(regenerado)
    return regenerados


def escribir_corpus(casos: list[dict], ruta: Path = DEFAULT_PATH) -> Path:
    """Congela los casos observados en `ruta`, conservando orden e ids (RF-5)."""
    congelados = []
    for caso in casos:
        nuevo = {"id": caso["id"]}
        if "fuente" in caso:
            nuevo["fuente"] = caso["fuente"]
        if "programa" in caso:
            nuevo["programa"] = caso["programa"]
        nuevo["resultado"] = caso["resultado"]
        if caso["resultado"] == "acepta":
            nuevo["sha256"] = caso["sha256"]
        congelados.append(nuevo)
    ruta = Path(ruta)
    ruta.write_text(
        json.dumps({"version": VERSION, "casos": congelados}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return ruta
