"""Pruebas del pipeline de generación y verificación (HU-04).

Especificación: specs/002-step-verificado/spec.md
- AC1: el programa pasa el verificador de constraint-kit sin errores.
- AC2: el STEP es un B-rep válido que se vuelve a leer (proxy local de FreeCAD).
- AC3: 5 casos con volumen y caja envolvente dentro de ±2 %.
- AC4: cada respuesta entrega STEP, GLB y lista de materiales en CSV.
- AC5: se registra el tiempo de generación y de construcción.
"""

import csv
import json
import math

import pytest

pytest.importorskip("cadquery")

from m2_cad import pipeline  # noqa: E402

TOLERANCIA = 0.02


def _programa(tipo: str, **params: float) -> dict:
    return {
        "parts": [{"id": "p", "type": tipo, "material": "steel", "params": params}],
        "mates": [],
    }


def _area_hexagono(entre_caras: float) -> float:
    lado = entre_caras / math.sqrt(3)
    return 3 * math.sqrt(3) / 2 * lado**2


def _area_circulo(diametro: float) -> float:
    return math.pi / 4 * diametro**2


# (programa, volumen esperado mm3, caja esperada mm) calculados a mano.
CASOS_TOLERANCIA = [
    pytest.param(
        _programa("adapter", bottom_w=40, bottom_d=40, top_d=24, height=30),
        29166.930055426,
        (40, 40, 30),
        id="adaptador-loft-caja-antes-de-teselar",
    ),
    pytest.param(
        _programa("spacer", outer_d=20, bore_d=8, height=15),
        (_area_circulo(20) - _area_circulo(8)) * 15,
        (20, 20, 15),
        id="espaciador",
    ),
    pytest.param(
        _programa("shaft", diameter=10, length=80),
        _area_circulo(10) * 80,
        (10, 10, 80),
        id="eje",
    ),
    pytest.param(
        _programa("washer", outer_d=24, bore_d=13, thick=2.5),
        (_area_circulo(24) - _area_circulo(13)) * 2.5,
        (24, 24, 2.5),
        id="arandela",
    ),
    pytest.param(
        _programa(
            "plate",
            width=120,
            depth=80,
            thick=10,
            boss_d=20,
            boss_h=5,
            bolt_d=6,
            bolt_circle=50,
            bolt_count=4,
        ),
        120 * 80 * 10 + _area_circulo(20) * 5 - 4 * _area_circulo(6) * 10,
        (120, 80, 15),
        id="placa",
    ),
    pytest.param(
        _programa("nut", af=13, height=6.5, bore_d=8),
        (_area_hexagono(13) - _area_circulo(8)) * 6.5,
        None,
        id="tuerca",
    ),
]


def test_verificar_programa_valido_sin_errores():
    """AC1: un programa del catálogo pasa el verificador sin errores."""
    informe = pipeline.verificar_programa(_programa("spacer"))

    assert informe["ok"] is True
    assert informe["n_errors"] == 0


def test_verificar_programa_invalido_lanza_error():
    """AC1: un programa con errores no avanza a la construcción."""
    with pytest.raises(pipeline.ErrorVerificacion):
        pipeline.verificar_programa(_programa("no_existe"))


def test_verificar_programa_declinado_lanza_declinacion():
    """Una declinación del modelo no se construye; el motivo va en español (HU-05)."""
    with pytest.raises(pipeline.PiezaDeclinada) as excinfo:
        pipeline.verificar_programa({"unsupported": "gear train"})

    assert excinfo.value.detalle == "gear train"
    assert excinfo.value.motivo.startswith("El asistente no puede construir esta pieza:")
    assert "«gear train»" in excinfo.value.motivo


def test_extraer_programa_ignora_razonamiento_previo():
    """La salida del modelo puede traer razonamiento antes del JSON."""
    programa = _programa("spacer", outer_d=14)
    salida = "Thinking about it...<channel|>" + json.dumps(programa) + "<turn|>"

    assert pipeline.extraer_programa(salida) == programa


def test_extraer_programa_sin_json_lanza_error():
    with pytest.raises(pipeline.ErrorGeneracion):
        pipeline.extraer_programa("no program here")


def test_construir_pieza_entrega_step_glb_csv(tmp_path):
    """AC2 y AC4: STEP válido, GLB y lista de materiales en CSV."""
    resultado = pipeline.construir_pieza(_programa("spacer"), tmp_path)

    assert resultado.step.suffix == ".step" and resultado.step.stat().st_size > 0
    assert resultado.glb.suffix == ".glb" and resultado.glb.stat().st_size > 0
    assert resultado.bom_csv.suffix == ".csv"
    assert resultado.step.parent == tmp_path

    import cadquery as cq

    forma = cq.importers.importStep(str(resultado.step)).val()
    assert forma.isValid()

    with open(resultado.bom_csv, encoding="utf-8") as archivo:
        filas = list(csv.reader(archivo))
    assert filas[0] == ["part_type", "qty", "total_mass_g", "unit_mass_g"]
    assert filas[1][:2] == ["spacer", "1"]


def test_construir_pieza_rechaza_programa_invalido(tmp_path):
    """AC1: nunca se exporta un programa que no pasa el verificador."""
    with pytest.raises(pipeline.ErrorVerificacion):
        pipeline.construir_pieza(_programa("no_existe"), tmp_path)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(("programa", "volumen", "caja"), CASOS_TOLERANCIA)
def test_volumen_y_caja_dentro_de_tolerancia(tmp_path, programa, volumen, caja):
    """AC3: volumen y caja envolvente dentro de ±2 % del valor esperado."""
    resultado = pipeline.construir_pieza(programa, tmp_path)

    assert resultado.volumen_mm3 == pytest.approx(volumen, rel=TOLERANCIA)
    if caja is not None:
        assert resultado.caja_mm == pytest.approx(caja, rel=TOLERANCIA)


def test_generar_pieza_registra_tiempos(tmp_path):
    """AC5: el resultado incluye el tiempo de generación y de construcción."""
    llamadas = []

    def planificar(texto: str) -> dict:
        llamadas.append(texto)
        return _programa("spacer")

    resultado = pipeline.generar_pieza(
        "un espaciador de acero",
        planificar=planificar,
        directorio=tmp_path,
    )

    assert llamadas == ["un espaciador de acero"]
    assert resultado.tiempo_generacion_s >= 0
    assert resultado.tiempo_construccion_s > 0
    assert resultado.step.parent.parent == tmp_path


def test_hu14_sin_traduccion_el_texto_en_espanol_llega_al_modelo(tmp_path):
    """HU-14 AC4: no hay paso de traducción; la respuesta no expone traducción."""
    import importlib.util

    resultado = pipeline.generar_pieza(
        "Placa de 120 mm con 4 agujeros",
        planificar=lambda texto: _programa("spacer"),
        directorio=tmp_path,
    )

    assert "traduccion" not in resultado.a_respuesta()
    assert not hasattr(resultado, "traduccion")
    assert importlib.util.find_spec("m2_cad.traduccion") is None


def test_a_respuesta_expone_archivos_y_tiempos(tmp_path):
    """AC4 y AC5: la respuesta de la API lleva los tres archivos y los tiempos."""
    resultado = pipeline.construir_pieza(_programa("spacer"), tmp_path)

    respuesta = resultado.a_respuesta()

    assert set(respuesta) >= {
        "step",
        "glb",
        "bom_csv",
        "volumen_mm3",
        "tiempo_generacion_s",
        "tiempo_construccion_s",
    }
    assert all(isinstance(valor, str) for valor in respuesta.values())


def test_planificar_con_llm_usa_servidor_configurado(monkeypatch):
    """El modelo servido (HU-01) se consulta en LLM_BASE_URL."""
    peticiones = []

    def chat_falso(cuerpo: dict, *, url: str, timeout: float) -> dict:
        peticiones.append((cuerpo, url))
        contenido = json.dumps(_programa("spacer"))
        return {"choices": [{"message": {"content": contenido}}]}

    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline.llm, "chat", chat_falso)

    programa = pipeline.planificar_con_llm("a steel spacer")

    assert programa == _programa("spacer")
    cuerpo, url = peticiones[0]
    assert url == "http://llama:8080"
    assert cuerpo["messages"][-1] == {"role": "user", "content": "a steel spacer"}


VARIABLES_LLM = (
    "LLM_BASE_URL",
    "PLANNER_URL",
    "QWEN_BASE_URL",
    "LLM_MODEL",
    "MODEL_PLANNER",
    "LLM_API_KEY",
    "DEEPSEEK_API_KEY",
)
CLAVE_FALSA = "sk-clave-de-prueba-secreta"


def _entorno_deepseek(monkeypatch, clave: str | None = CLAVE_FALSA) -> None:
    for variable in VARIABLES_LLM:
        monkeypatch.delenv(variable, raising=False)
    if clave:
        monkeypatch.setenv("DEEPSEEK_API_KEY", clave)


def test_hu14_por_defecto_usa_deepseek_con_el_texto_en_espanol(monkeypatch):
    """HU-14 AC1: sin LLM_BASE_URL se consulta DeepSeek con su modelo por defecto."""
    peticiones = []

    def chat_falso(cuerpo: dict, *, url: str, timeout: float) -> dict:
        peticiones.append((cuerpo, url))
        return {"choices": [{"message": {"content": json.dumps(_programa("spacer"))}}]}

    _entorno_deepseek(monkeypatch)
    monkeypatch.setattr(pipeline.llm, "chat", chat_falso)

    programa = pipeline.planificar_con_llm("un espaciador de acero")

    assert programa == _programa("spacer")
    cuerpo, url = peticiones[0]
    assert url == "https://api.deepseek.com"
    assert cuerpo["model"] == "deepseek-v4-pro"
    assert cuerpo["response_format"] == {"type": "json_object"}
    assert cuerpo["messages"][-1] == {"role": "user", "content": "un espaciador de acero"}


def test_hu14_sin_api_key_de_deepseek_no_llama_al_modelo(monkeypatch):
    """HU-14 AC3: sin DEEPSEEK_API_KEY se informa en español y no hay petición."""
    llamadas = []
    _entorno_deepseek(monkeypatch, clave=None)
    monkeypatch.setattr(pipeline.llm, "chat", lambda *a, **k: llamadas.append(a))

    with pytest.raises(pipeline.ModeloNoDisponible, match="DEEPSEEK_API_KEY"):
        pipeline.planificar_con_llm("un espaciador")
    assert llamadas == []


@pytest.mark.parametrize(
    ("codigo", "fragmento"),
    [
        pytest.param(401, "API key", id="401-clave-invalida"),
        pytest.param(402, "saldo", id="402-sin-saldo"),
        pytest.param(429, "límite", id="429-limite"),
        pytest.param(503, "HTTP 503", id="503-otro-estado"),
    ],
)
def test_hu14_errores_http_de_deepseek_en_espanol_sin_la_clave(monkeypatch, codigo, fragmento):
    """HU-14 AC2 y AC3: el error HTTP se explica en español y nunca expone la key."""
    import httpx

    peticion = httpx.Request(
        "POST",
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {CLAVE_FALSA}"},
    )
    respuesta = httpx.Response(codigo, request=peticion, text=CLAVE_FALSA)

    def chat_fallido(cuerpo, *, url, timeout):
        raise httpx.HTTPStatusError(str(codigo), request=peticion, response=respuesta)

    _entorno_deepseek(monkeypatch)
    monkeypatch.setattr(pipeline.llm, "chat", chat_fallido)

    with pytest.raises(pipeline.ModeloNoDisponible) as excinfo:
        pipeline.planificar_con_llm("un espaciador")

    assert fragmento in str(excinfo.value)
    assert CLAVE_FALSA not in str(excinfo.value)


def test_hu14_tiempo_de_espera_en_espanol(monkeypatch):
    """HU-14 AC3: un timeout de DeepSeek se informa como modelo no disponible."""
    import httpx

    def chat_lento(cuerpo, *, url, timeout):
        raise httpx.ReadTimeout("timed out")

    _entorno_deepseek(monkeypatch)
    monkeypatch.setattr(pipeline.llm, "chat", chat_lento)

    with pytest.raises(pipeline.ModeloNoDisponible, match="a tiempo"):
        pipeline.planificar_con_llm("un espaciador")


@pytest.mark.parametrize(
    ("salida", "esperado"),
    [
        pytest.param(
            '{"unsupported": "needs a } brace"}',
            {"unsupported": "needs a } brace"},
            id="llave-de-cierre-en-texto",
        ),
        pytest.param(
            'reasoning {draft} <channel|>{"parts": [], "mates": [], "note": "a { b"}',
            {"parts": [], "mates": [], "note": "a { b"},
            id="llave-de-apertura-en-texto",
        ),
        pytest.param(
            '{"a": 1} then the final answer {"parts": [], "mates": []} done',
            {"parts": [], "mates": []},
            id="ultimo-objeto",
        ),
        pytest.param(
            'draft {not json} answer {"parts": [], "mates": []}',
            {"parts": [], "mates": []},
            id="llave-que-no-abre-json",
        ),
    ],
)
def test_extraer_programa_respeta_llaves_dentro_de_strings(salida, esperado):
    """Las llaves dentro de cadenas JSON no rompen la extracción."""
    assert pipeline.extraer_programa(salida) == esperado


def test_hu14_prompt_cubre_el_catalogo_y_acepta_espanol():
    """HU-14 AC6: el prompt describe el DSL de cada tipo del catálogo y admite español."""
    prompt = pipeline.PROMPT_SISTEMA

    for tipo in pipeline.CATALOGO:
        assert f"{tipo}{{" in prompt, tipo
    assert "Spanish" in prompt
    assert "JSON" in prompt
    assert "unsupported" in prompt


def test_generar_pieza_separa_tiempo_de_generacion_y_construccion(tmp_path, monkeypatch):
    """AC5: la generación mide el modelo y excluye la construcción."""
    import time

    espera_generacion = 0.1
    espera_construccion = 0.3
    construir_real = pipeline.construir_pieza

    def planificar_lento(texto: str) -> dict:
        time.sleep(espera_generacion)
        return _programa("spacer")

    def construir_lento(programa: dict, directorio):
        time.sleep(espera_construccion)
        return construir_real(programa, directorio)

    monkeypatch.setattr(pipeline, "construir_pieza", construir_lento)

    resultado = pipeline.generar_pieza(
        "un espaciador",
        planificar=planificar_lento,
        directorio=tmp_path,
    )

    assert espera_generacion <= resultado.tiempo_generacion_s < espera_construccion


def _configurar_chat(monkeypatch, chat):
    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline.llm, "chat", chat)


@pytest.mark.parametrize(
    "error",
    [
        pytest.param("timeout", id="tiempo-de-espera"),
        pytest.param("conexion", id="conexion-caida"),
        pytest.param("http", id="error-http"),
    ],
)
def test_planificar_con_llm_falla_de_red_es_modelo_no_disponible(monkeypatch, error):
    """Los fallos de red del modelo servido se informan como ModeloNoDisponible."""
    import httpx

    peticion = httpx.Request("POST", "http://llama:8080/chat/completions")
    errores = {
        "timeout": httpx.ReadTimeout("timed out", request=peticion),
        "conexion": httpx.ConnectError("refused", request=peticion),
        "http": httpx.HTTPStatusError(
            "500", request=peticion, response=httpx.Response(500, request=peticion)
        ),
    }

    def chat_fallido(cuerpo, *, url, timeout):
        raise errores[error]

    _configurar_chat(monkeypatch, chat_fallido)

    with pytest.raises(pipeline.ModeloNoDisponible):
        pipeline.planificar_con_llm("a spacer")


def test_planificar_con_llm_respuesta_malformada_es_error_de_generacion(monkeypatch):
    _configurar_chat(monkeypatch, lambda cuerpo, *, url, timeout: {"choices": []})

    with pytest.raises(pipeline.ErrorGeneracion):
        pipeline.planificar_con_llm("a spacer")


def test_planificar_con_llm_no_oculta_errores_de_programacion(monkeypatch):
    """Un error que no es de red no se disfraza de modelo no disponible."""

    def chat_con_bug(cuerpo, *, url, timeout):
        raise ValueError("bug")

    _configurar_chat(monkeypatch, chat_con_bug)

    with pytest.raises(ValueError, match="bug"):
        pipeline.planificar_con_llm("a spacer")


# --- HU-05: declinación con motivo y marca de diseño preliminar ---------------
# Especificación: specs/003-declinacion-preliminar/spec.md (AC1-AC4).

MARCA = "Diseño preliminar, requiere revisión profesional"


def _caso_banco(identificador: str) -> dict:
    from m2_cad.dataset import read_dataset

    return next(fila for fila in read_dataset() if fila["id"] == identificador)


def _programa_del_banco(identificador: str) -> dict:
    medidas = json.loads(_caso_banco(identificador)["medidas"])
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


def _ensamble_dos_placas() -> dict:
    return {
        "parts": [
            {"id": "base", "type": "plate", "params": {"width": 60, "depth": 60, "thick": 5}},
            {"id": "tapa", "type": "plate", "params": {"width": 40, "depth": 40, "thick": 5}},
        ],
        "mates": [{"a": "base", "b": "tapa", "intent": "seat_on"}],
    }


def _descripcion_step(ruta) -> str:
    """Devuelve FILE_DESCRIPTION del STEP con las cadenas \\X2\\ decodificadas."""
    import re

    cabecera = ruta.read_text(encoding="ascii").split("ENDSEC;")[0]
    descripcion = re.search(r"FILE_DESCRIPTION\(\('(.*?)'\)", cabecera, re.S).group(1)
    return re.sub(
        r"\\X2\\((?:[0-9A-F]{4})+)\\X0\\",
        lambda m: "".join(
            chr(int(m.group(1)[i : i + 4], 16)) for i in range(0, len(m.group(1)), 4)
        ),
        descripcion,
    )


# (caso del banco HU-02, salida simulada del modelo): cada vía de declinación.
CASOS_FUERA_DE_CATALOGO = [
    pytest.param("HU02-N01", {"unsupported": "structural certification"}, id="no-soportado"),
    pytest.param("HU02-N04", _programa("panel", width=900, depth=10, height=600), id="tipo-ajeno"),
    pytest.param("HU02-N06", _ensamble_dos_placas(), id="ensamblaje"),
]


@pytest.mark.parametrize(("identificador", "salida_modelo"), CASOS_FUERA_DE_CATALOGO)
def test_hu05_fuera_de_catalogo_se_declina_en_espanol_sin_step(
    tmp_path, identificador, salida_modelo
):
    """AC1: 3/3 solicitudes fuera del catálogo se declinan con motivo y sin STEP."""
    with pytest.raises(pipeline.PiezaDeclinada) as excinfo:
        pipeline.generar_pieza(
            _caso_banco(identificador)["solicitud"],
            planificar=lambda texto: salida_modelo,
            directorio=tmp_path,
        )

    motivo = excinfo.value.motivo
    assert motivo.startswith("El asistente no puede construir esta pieza:")
    assert "fuera del catálogo" in motivo or "fuera del alcance" in motivo
    assert list(tmp_path.rglob("*.step")) == []


@pytest.mark.parametrize(
    "identificador", ["HU02-P01", "HU02-P06", "HU02-P11", "HU02-P21", "HU02-P26"]
)
def test_hu05_catalogo_no_se_declina_y_lleva_marca(tmp_path, identificador):
    """AC2 y AC3: 0/5 piezas del catálogo se declinan y toda salida lleva la marca."""
    resultado = pipeline.generar_pieza(
        _caso_banco(identificador)["solicitud"],
        planificar=lambda texto: _programa_del_banco(identificador),
        directorio=tmp_path,
    )

    assert resultado.step.is_file()
    assert _descripcion_step(resultado.step) == MARCA
    assert resultado.a_respuesta()["aviso"] == MARCA


def test_hu05_step_marcado_sigue_siendo_valido(tmp_path):
    """AC3: la marca en la cabecera no rompe la lectura del B-rep."""
    import cadquery as cq

    resultado = pipeline.construir_pieza(_programa("spacer"), tmp_path)

    assert _descripcion_step(resultado.step) == MARCA
    assert cq.importers.importStep(str(resultado.step)).val().isValid()
