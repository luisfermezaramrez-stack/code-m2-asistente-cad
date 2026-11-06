"""Traducción de solicitudes CAD español-inglés (HU-03)."""

import json
import os
import re
from collections import Counter
from urllib.request import Request, urlopen

MODELO = "gemini-3.5-flash-lite"
URL_GEMINI = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent"
TIEMPO_ESPERA = 8
LONGITUD_MAXIMA = 1000

# Protege cifras y unidades, incluso sin espacios (ej. 12,5mm).
PATRON_VALOR = re.compile(
    r"\d+(?:[.,]\d+)?(?:[ \t]*(?:mm|cm|kg|g|m)\b)?",
    re.IGNORECASE,
)
PATRON_MARCADOR = re.compile(r"__CADVAL_\d+__")
PATRON_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


class ErrorTraduccion(RuntimeError):
    """Error al consultar o validar una traducción técnica."""


def _proteger_valores(texto: str) -> tuple[str, dict[str, str]]:
    """Reemplaza cantidades y unidades por marcadores reversibles."""
    valores: dict[str, str] = {}

    def reemplazar(coincidencia: re.Match[str]) -> str:
        marcador = f"__CADVAL_{len(valores)}__"
        valores[marcador] = coincidencia.group()
        return marcador

    return PATRON_VALOR.sub(reemplazar, texto), valores


def _consultar_gemini(texto_protegido: str, clave: str) -> str:
    """Solicita la traducción y rechaza respuestas incompletas."""
    instrucciones = (
        "Translate this CAD component description from Spanish to English. "
        "Keep every __CADVAL_N__ placeholder unchanged and exactly once. "
        "Do not add dimensions or components. Return only the translation:\n"
        f"{texto_protegido}"
    )
    datos = {
        "contents": [{"parts": [{"text": instrucciones}]}],
        "generationConfig": {"temperature": 0},
    }
    solicitud = Request(
        URL_GEMINI,
        data=json.dumps(datos).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": clave,
        },
        method="POST",
    )

    try:
        with urlopen(solicitud, timeout=TIEMPO_ESPERA) as respuesta:
            resultado = json.load(respuesta)
    except (OSError, json.JSONDecodeError) as exc:
        raise ErrorTraduccion("No fue posible consultar Gemini.") from exc

    try:
        candidato = resultado["candidates"][0]
        if candidato.get("finishReason") != "STOP":
            raise ErrorTraduccion("Gemini no finalizó la traducción correctamente.")

        partes = candidato["content"]["parts"]
        traduccion = "".join(parte["text"] for parte in partes if not parte.get("thought"))
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ErrorTraduccion("Gemini devolvió una respuesta sin texto válido.") from exc

    if not traduccion.strip():
        raise ErrorTraduccion("Gemini devolvió una traducción vacía.")

    return traduccion.strip()


def _restaurar_valores(
    traduccion: str,
    original: str,
    valores: dict[str, str],
) -> str:
    """Restaura las cantidades y comprueba los valores numéricos."""
    marcadores = PATRON_MARCADOR.findall(traduccion)

    if Counter(marcadores) != Counter(valores.keys()):
        raise ErrorTraduccion("Gemini modificó los marcadores de las medidas.")

    for marcador, valor in valores.items():
        traduccion = traduccion.replace(marcador, valor)

    if Counter(PATRON_NUMERO.findall(original)) != Counter(PATRON_NUMERO.findall(traduccion)):
        raise ErrorTraduccion("La traducción alteró las cantidades originales.")

    return traduccion


def traducir_solicitud(texto: str) -> str:
    """Traduce una solicitud CAD conservando cantidades y unidades."""
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("La solicitud debe contener texto.")

    texto = texto.strip()

    if len(texto) > LONGITUD_MAXIMA:
        raise ValueError("La solicitud supera el límite de 1000 caracteres.")

    clave = os.getenv("GEMINI_API_KEY")
    if not clave:
        raise ErrorTraduccion("No se ha configurado GEMINI_API_KEY.")

    protegido, valores = _proteger_valores(texto)
    traduccion = _consultar_gemini(protegido, clave)

    return _restaurar_valores(traduccion, texto, valores)
