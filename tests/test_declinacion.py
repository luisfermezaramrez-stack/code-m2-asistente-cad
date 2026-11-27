"""Motivo de declinación legible y etiquetado por causa (HU-26, SPEC-027).

AC1: cada caso esperado como declinación recibe exactamente una causa del catálogo.
AC2: el mensaje al usuario está en español, no contiene identificadores del DSL ni
mensajes crudos del verificador, e indica qué haría falta para aceptar la solicitud.

Sin red, API key ni GPU (RNF-1): los casos parten de programas, no de texto.
"""

import pytest

from m2_cad import declinacion, pipeline

# RF-1: catálogo mínimo exigido por la especificación.
CAUSAS_OBLIGATORIAS = {
    "familia_no_soportada",
    "dimension_incoherente",
    "verificacion_fallida",
    "fuera_de_tolerancia",
    "texto_ambiguo",
}

# Identificadores del DSL, del verificador y del propio código que AC2 prohíbe en el
# mensaje del usuario. Se comparan en minúsculas y como subcadena.
TERMINOS_TECNICOS = (
    "unsupported",
    "parts",
    "parte ",
    "params",
    "mate",
    "defs",
    "anchor",
    "dsl",
    "constraint",
    "severity",
    "diagnostic",
    "verificador",
    "programa",
    "plate",
    "sheet_bracket",
    "adapter",
    "flange",
    "spacer",
    "screw",
    "extrusion",
    "pipe",
    "bore_d",
    "outer_d",
    "error",
)

# Casos esperados como declinación, con la causa que el catálogo debe asignarles.
# El primer caso reproduce la forma del corpus dorado (SPEC-024: `resultado:
# "declina"` con programa `{"unsupported": "<motivo>"}`); el resto recorre cada
# camino que hoy puede declinar una solicitud.
CASOS_DECLINACION = [
    pytest.param(
        {"unsupported": "gear train"},
        declinacion.Causa.FAMILIA_NO_SOPORTADA,
        id="corpus-no-soportado",
    ),
    pytest.param(
        {"parts": [{"id": "p", "type": "plate", "params": {"width": -5, "depth": 30, "thick": 5}}]},
        declinacion.Causa.DIMENSION_INCOHERENTE,
        id="medidas-incoherentes",
    ),
    pytest.param(
        {"parts": [{"id": "p", "type": "plate"}], "mates": [{"a": "p", "b": "q"}]},
        declinacion.Causa.VERIFICACION_FALLIDA,
        id="estructura-invalida",
    ),
    pytest.param(
        {"parts": [{"id": "p", "type": "no_existe"}]},
        declinacion.Causa.FAMILIA_NO_SOPORTADA,
        id="tipo-ajeno-al-verificador",
    ),
    pytest.param(
        {"parts": [{"id": "p", "type": "nut", "params": {}}]},
        declinacion.Causa.FAMILIA_NO_SOPORTADA,
        id="tipo-fuera-del-catalogo",
    ),
    pytest.param(
        {"parts": [{"id": "a", "type": "plate"}, {"id": "b", "type": "plate"}]},
        declinacion.Causa.FAMILIA_NO_SOPORTADA,
        id="ensamblaje",
    ),
]


def _declinacion_de(programa: dict) -> pipeline.PiezaDeclinada | pipeline.ErrorVerificacion:
    """Declinación que produce el pipeline para un programa, con su causa."""
    with pytest.raises((pipeline.PiezaDeclinada, pipeline.ErrorVerificacion)) as excinfo:
        pipeline.validar_catalogo(programa)
        pipeline.verificar_programa(programa)
    return excinfo.value


def test_el_catalogo_es_cerrado_y_completo():
    """RF-1: el catálogo contiene al menos las cinco causas y cada una explica qué hacer."""
    assert {causa.value for causa in declinacion.Causa} >= CAUSAS_OBLIGATORIAS
    assert declinacion.NINGUNA not in {causa.value for causa in declinacion.Causa}

    for causa in declinacion.Causa:
        mensaje = declinacion.mensaje(causa)
        assert mensaje.startswith(declinacion.PREFIJO)
        assert mensaje.endswith(".")
        assert declinacion.QUE_HARIA_FALTA[causa] in mensaje


@pytest.mark.parametrize(("programa", "causa_esperada"), CASOS_DECLINACION)
def test_ac1_cada_declinacion_recibe_una_causa_del_catalogo(programa, causa_esperada):
    """AC1: cada caso esperado como declinación tiene una causa del catálogo."""
    declinada = _declinacion_de(programa)

    assert isinstance(declinada.causa, declinacion.Causa)
    assert declinada.causa is causa_esperada
    assert declinada.causa.value in CAUSAS_OBLIGATORIAS


@pytest.mark.parametrize(("programa", "causa_esperada"), CASOS_DECLINACION)
def test_ac2_el_mensaje_al_usuario_es_claro_y_accionable(programa, causa_esperada):
    """AC2: mensaje en español, sin jerga del DSL ni del verificador, con qué hacer."""
    declinada = _declinacion_de(programa)
    mensaje = declinada.mensaje

    assert mensaje
    assert declinacion.QUE_HARIA_FALTA[causa_esperada] in mensaje
    for termino in TERMINOS_TECNICOS:
        assert termino not in mensaje.lower(), f"«{termino}» no puede aparecer en el mensaje"
    # RF-5: el detalle técnico se conserva, pero fuera del mensaje principal.
    if declinada.detalle:
        assert declinada.detalle not in mensaje


def test_el_texto_ambiguo_tambien_recibe_causa_y_mensaje_legible():
    """AC1 y AC2: una salida del modelo sin programa se explica sin jerga."""
    with pytest.raises(pipeline.ErrorGeneracion) as excinfo:
        pipeline.extraer_programa("no hay ningún objeto json aquí")

    assert excinfo.value.causa is declinacion.Causa.TEXTO_AMBIGUO
    assert declinacion.QUE_HARIA_FALTA[declinacion.Causa.TEXTO_AMBIGUO] in excinfo.value.mensaje


@pytest.mark.parametrize(
    ("informe", "causa_esperada"),
    [
        pytest.param(
            {"declined": True, "n_errors": 0, "diagnostics": []},
            declinacion.Causa.FAMILIA_NO_SOPORTADA,
            id="rechazo-honesto",
        ),
        pytest.param(
            {
                "declined": False,
                "n_errors": 1,
                "diagnostics": [{"severity": "error", "code": "unknown-part-type"}],
            },
            declinacion.Causa.FAMILIA_NO_SOPORTADA,
            id="tipo-desconocido",
        ),
        pytest.param(
            {
                "declined": False,
                "n_errors": 1,
                "diagnostics": [{"severity": "error", "code": "part-build-error"}],
            },
            declinacion.Causa.DIMENSION_INCOHERENTE,
            id="medidas-no-construibles",
        ),
        pytest.param(
            {
                "declined": False,
                "n_errors": 2,
                "diagnostics": [
                    {"severity": "error", "code": "part-build-error"},
                    {"severity": "error", "code": "duplicate-id"},
                ],
            },
            declinacion.Causa.DIMENSION_INCOHERENTE,
            id="medidas-manda-sobre-estructura",
        ),
        pytest.param(
            {
                "declined": False,
                "n_errors": 1,
                "diagnostics": [{"severity": "error", "code": "bad-mate"}],
            },
            declinacion.Causa.VERIFICACION_FALLIDA,
            id="error-estructural",
        ),
        pytest.param(
            {
                "declined": False,
                "n_errors": 0,
                "diagnostics": [{"severity": "warning", "code": "missing-joint"}],
            },
            declinacion.Causa.VERIFICACION_FALLIDA,
            id="sin-errores",
        ),
    ],
)
def test_la_causa_sale_de_los_codigos_estructurados_del_verificador(informe, causa_esperada):
    """RF-2: la clasificación usa el código del verificador, nunca el texto libre."""
    assert declinacion.causa_de_informe(informe) is causa_esperada


def test_los_adaptadores_de_la_api_propagan_la_causa(monkeypatch):
    """AC3: la causa viaja en el mismo `medido` que cierra la corrida, en las dos rutas."""
    pytest.importorskip("cadquery")
    from m2_cad import api
    from m2_cad.control import ControlGeneracion

    def declinar(texto, **kwargs):
        raise pipeline.PiezaDeclinada(
            "fuera del catálogo", causa=declinacion.Causa.FAMILIA_NO_SOPORTADA
        )

    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline, "generar_pieza", declinar)

    medido_json: dict = {}
    with pytest.raises(api.DeclinacionSolicitud):
        api.procesar_con_pipeline("Ensamble de dos bridas", medido_json)
    assert medido_json["causa"] == "familia_no_soportada"

    medido_sse: dict = {}
    with pytest.raises(api.SolicitudDeclinada):
        api.procesar_con_progreso(
            "Ensamble de dos bridas", ControlGeneracion(lambda etapa: None), medido_sse
        )
    assert medido_sse["causa"] == "familia_no_soportada"


def test_el_catalogo_solo_crece_agregando_causas():
    """S13: una causa nueva entra al catálogo con su mensaje, nunca como texto libre."""
    for causa in declinacion.Causa:
        assert causa.value == causa.value.lower()
        assert " " not in causa.value


def test_ac1_los_casos_declinados_del_corpus_dorado_reciben_causa():
    """AC1: los casos `declina` del corpus real (SPEC-024) tienen causa del catálogo."""
    from m2_cad import corpus_dorado

    casos = [caso for caso in corpus_dorado.cargar_corpus() if caso["resultado"] == "declina"]

    assert casos, "el corpus dorado no declara casos de declinación"
    for caso in casos:
        declinada = _declinacion_de(corpus_dorado.programa_de_caso(caso))
        assert isinstance(declinada.causa, declinacion.Causa), caso["id"]


def test_el_detalle_tecnico_se_conserva_en_el_log(tmp_path, monkeypatch, caplog):
    """RF-5: el detalle técnico queda para diagnóstico, fuera del mensaje y del registro."""
    import logging

    pytest.importorskip("cadquery")
    from m2_cad import api

    detalle = "part-build-error at parts[0].params: bore 20 > outer_d 10"

    def fallar(texto, **kwargs):
        raise pipeline.ErrorVerificacion(detalle, causa=declinacion.Causa.DIMENSION_INCOHERENTE)

    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline, "generar_pieza", fallar)

    with caplog.at_level(logging.WARNING), pytest.raises(api.FalloHTTP) as excinfo:
        api.procesar_con_pipeline("Espaciador con agujero grande", {})

    assert detalle not in str(excinfo.value.detail)
    assert detalle in caplog.text


def test_el_worker_registra_la_causa_del_trabajo_declinado(tmp_path):
    """AC3 en la cola persistente: la fila del worker lleva la causa estructurada."""
    from datetime import UTC, datetime

    from m2_cad import seguimiento, worker

    ruta = tmp_path / "registro.csv"
    trabajo = {
        "id": "trabajo-1",
        "texto": "Ensamble de dos bridas",
        "creado_en": datetime.now(UTC).isoformat(),
        "usuario": "ana",
        "request_id": "req-1",
    }
    terminal = {
        "solicitud_id": "trabajo-1",
        "estado": "declinado",
        "motivo": "la solicitud está fuera del catálogo del asistente",
        "codigo_http": 422,
    }

    worker.registrar_terminal(
        trabajo,
        terminal,
        {"causa": "familia_no_soportada"},
        seguimiento.Configuracion(activo=False),
        ruta,
    )

    import csv

    with ruta.open(newline="", encoding="utf-8") as archivo:
        fila = next(csv.DictReader(archivo))
    assert fila["causa"] == "familia_no_soportada"
    assert fila["error"] == terminal["motivo"]
