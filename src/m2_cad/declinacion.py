"""Catálogo cerrado de causas de declinación (HU-26, SPEC-027).

Una declinación decía *por qué* en texto libre: la razón cruda del modelo o los
mensajes del verificador. Ese texto servía para diagnosticar, pero no explicaba
nada al usuario ni se podía usar como dimensión de métricas (RF-4, AC3).

Aquí viven, en un solo lugar y sin duplicarse en el pipeline ni en la API:

- `Causa`: la etiqueta estructurada, cerrada y estable (RF-1, RF-2).
- `MOTIVO` y `QUE_HARIA_FALTA`: las dos frases del mensaje al usuario, en español,
  sin términos internos, la segunda con lo que haría falta para aceptar la
  solicitud (RF-3, AC2).
- `causa_de_informe`: la tabla que traduce el informe estructurado de
  `constraint-kit.dsl.check` a una causa. Nunca clasifica texto libre.

Especificación: specs/027-hu-26-declinacion-legible/spec.md
HU-48 (SPEC-049, RF-5) agrega `MATERIAL_NO_SOPORTADO`: el material pedido está fuera del
catálogo cerrado del planificador y el motivo debe nombrarlo.
"""

from enum import StrEnum

# Valor del registro cuando la solicitud no se declinó (SPEC-004 AC3: sin vacíos).
NINGUNA = "ninguna"

PREFIJO = "El asistente no puede construir esta pieza:"

# Códigos estructurados del verificador que deciden la causa (nunca su texto libre).
_CODIGOS_MEDIDAS = frozenset({"part-build-error"})
_CODIGOS_FAMILIA = frozenset({"unknown-part-type"})


class Causa(StrEnum):
    """Causa de una declinación; cada solicitud rechazada tiene exactamente una."""

    FAMILIA_NO_SOPORTADA = "familia_no_soportada"
    MATERIAL_NO_SOPORTADO = "material_no_soportado"
    DIMENSION_INCOHERENTE = "dimension_incoherente"
    VERIFICACION_FALLIDA = "verificacion_fallida"
    FUERA_DE_TOLERANCIA = "fuera_de_tolerancia"
    TEXTO_AMBIGUO = "texto_ambiguo"


# Qué pasó, en palabras del usuario (RF-3). Sin nombres de tipos, parámetros ni
# códigos: el usuario no conoce el lenguaje interno ni el verificador.
MOTIVO = {
    Causa.FAMILIA_NO_SOPORTADA: "la solicitud está fuera del catálogo del asistente",
    Causa.MATERIAL_NO_SOPORTADO: "el material que pediste no está entre los soportados",
    Causa.DIMENSION_INCOHERENTE: "las medidas que pediste no forman una pieza construible",
    Causa.VERIFICACION_FALLIDA: "la pieza no superó la revisión geométrica con las medidas dadas",
    Causa.FUERA_DE_TOLERANCIA: "la pieza no coincide con el catálogo dentro de la tolerancia",
    Causa.TEXTO_AMBIGUO: "no se pudo entender qué pieza construir con la descripción",
}

# Qué haría falta para aceptar la solicitud (RF-3, AC2).
QUE_HARIA_FALTA = {
    Causa.FAMILIA_NO_SOPORTADA: (
        "Para aceptarla, pide una sola pieza de las familias del catálogo, "
        "con sus medidas en milímetros."
    ),
    Causa.MATERIAL_NO_SOPORTADO: (
        "Para aceptarla, indica el material de la pieza con uno de los nombres del "
        "catálogo soportado."
    ),
    Causa.DIMENSION_INCOHERENTE: (
        "Para aceptarla, revisa las medidas en milímetros para que formen una pieza "
        "posible: un agujero no puede ser mayor que la pieza que lo contiene."
    ),
    Causa.VERIFICACION_FALLIDA: (
        "Para aceptarla, describe una sola pieza con su tipo y todas sus medidas "
        "numéricas en milímetros."
    ),
    Causa.FUERA_DE_TOLERANCIA: (
        "Para aceptarla, usa medidas en milímetros dentro de las proporciones "
        "habituales del catálogo."
    ),
    Causa.TEXTO_AMBIGUO: (
        "Para aceptarla, indica qué pieza quieres y sus medidas en milímetros, por "
        "ejemplo: «placa de 120 mm por 80 mm y 10 mm de espesor»."
    ),
}


def normalizar(valor: object) -> str:
    """Valida una causa antes de persistirla: el catálogo es cerrado (RF-1, S13).

    Un valor ajeno al catálogo no se guarda como texto libre: es un defecto de quien
    llama y debe verse, no convertirse en una dimensión de métricas inválida.
    """
    texto = NINGUNA if valor is None else str(valor).strip()
    if not texto:
        return NINGUNA
    if texto != NINGUNA and texto not in {causa.value for causa in Causa}:
        raise ValueError(f"«{texto}» no es una causa del catálogo de declinación.")
    return texto


def causa_de_informe(informe: dict) -> Causa:
    """Traduce el informe del verificador a una causa del catálogo (RF-2).

    Sólo usa evidencia estructurada —el rechazo honesto del modelo y el código de
    cada diagnóstico—, así que la asignación es determinista. Prioridad: un rechazo
    del modelo o medidas no construibles explican mejor la declinación que un fallo
    estructural del programa.
    """
    if informe.get("declined"):
        return Causa.FAMILIA_NO_SOPORTADA
    codigos = {
        diagnostico.get("code")
        for diagnostico in informe.get("diagnostics") or ()
        if diagnostico.get("severity") == "error"
    }
    if codigos & _CODIGOS_MEDIDAS:
        return Causa.DIMENSION_INCOHERENTE
    if codigos and codigos <= _CODIGOS_FAMILIA:
        return Causa.FAMILIA_NO_SOPORTADA
    return Causa.VERIFICACION_FALLIDA


def mensaje(causa: Causa, contexto: str | None = None, *, catalogo: str = "") -> str:
    """Mensaje al usuario para una causa: qué pasó y qué haría falta (RF-3).

    `contexto` sólo admite texto legible ya redactado en español; el detalle técnico
    (razón del modelo, diagnostico del verificador) viaja por separado y nunca se
    muestra como mensaje principal (RF-5).
    """
    causa = Causa(causa)
    motivo = (contexto or MOTIVO[causa]).strip().rstrip(".")
    familias = ""
    if catalogo and causa is Causa.FAMILIA_NO_SOPORTADA:
        familias = f" Solo construye una pieza única de estas familias: {catalogo}."
    return f"{PREFIJO} {motivo}.{familias} {QUE_HARIA_FALTA[causa]}"
