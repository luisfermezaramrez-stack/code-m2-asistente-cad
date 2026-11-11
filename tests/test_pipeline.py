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
    """Una declinación del modelo no se construye y conserva su motivo."""
    with pytest.raises(pipeline.PiezaDeclinada) as excinfo:
        pipeline.verificar_programa({"unsupported": "gear train"})

    assert excinfo.value.motivo == "gear train"


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

    def traducir(texto: str) -> str:
        llamadas.append(("traducir", texto))
        return "a steel spacer"

    def planificar(texto_en: str) -> dict:
        llamadas.append(("planificar", texto_en))
        return _programa("spacer")

    resultado = pipeline.generar_pieza(
        "un espaciador de acero",
        traducir=traducir,
        planificar=planificar,
        directorio=tmp_path,
    )

    assert llamadas == [
        ("traducir", "un espaciador de acero"),
        ("planificar", "a steel spacer"),
    ]
    assert resultado.traduccion == "a steel spacer"
    assert resultado.tiempo_generacion_s >= 0
    assert resultado.tiempo_construccion_s > 0
    assert resultado.step.parent.parent == tmp_path


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


def test_planificar_con_llm_sin_servidor_lanza_error(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    with pytest.raises(pipeline.ModeloNoDisponible):
        pipeline.planificar_con_llm("a steel spacer")
