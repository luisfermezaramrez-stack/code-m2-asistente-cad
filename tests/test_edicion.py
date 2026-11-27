"""Pruebas del camino de edición del pipeline (HU-35, SPEC-036).

Sin red, sin GPU y sin API key: el modelo se simula con `planificar=` o
sustituyendo `llm_resiliente.consultar`.
- AC1 (S1, S3): una edición verificada entrega una pieza nueva, en un directorio
  nuevo, con el diff del programa DSL y la versión anterior intacta.
- AC2 (S6): una edición que rompe la verificación declina con la causa de
  SPEC-027 y no construye ni sobrescribe nada.
- S9: el modelo recibe el prompt de edición versionado y el programa previo.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("cadquery")

from m2_cad import declinacion, llm_resiliente, pipeline, versiones  # noqa: E402


def _placa(thick: float) -> dict:
    """Placa del catálogo con el espesor indicado."""
    return {
        "parts": [
            {
                "id": "p",
                "type": "plate",
                "material": "steel",
                "params": {"width": 80, "depth": 60, "thick": thick},
            }
        ],
        "mates": [],
    }


def _espaciador(height: float = 10) -> dict:
    """Espaciador del catálogo (pieza simple y rápida de construir)."""
    return {
        "parts": [
            {
                "id": "p",
                "type": "spacer",
                "material": "steel",
                "params": {"outer_d": 14, "bore_d": 0, "height": height},
            }
        ],
        "mates": [],
    }


def test_una_edicion_verificada_entrega_una_pieza_nueva_con_su_diff(tmp_path):
    """AC1/S3: la edición se construye y verifica en un directorio nuevo."""
    previo = _placa(5)
    anterior = pipeline.generar_pieza(
        "placa de 80 mm por 60 mm y 5 mm de espesor",
        planificar=lambda texto: previo,
        directorio=tmp_path,
    )
    nuevo = _placa(10)

    resultado = pipeline.editar_pieza(
        previo,
        "hazla 5 mm más gruesa",
        planificar=lambda texto: nuevo,
        directorio=tmp_path,
    )

    assert isinstance(resultado, pipeline.ResultadoPieza)
    assert resultado.programa["parts"][0]["params"]["thick"] == 10
    assert resultado.familia == "plate"
    assert resultado.step.exists() and resultado.glb.exists() and resultado.bom_csv.exists()
    carpeta = resultado.step.parent
    assert carpeta.parent == tmp_path
    assert carpeta != anterior.step.parent
    assert resultado.programa_json == carpeta / "programa.json"
    assert resultado.programa_json.exists()
    # La versión anterior se conserva intacta.
    assert anterior.step.exists() and anterior.glb.exists()
    assert versiones.diff_programas(previo, resultado.programa) == [
        {"ruta": "parts[0].params.thick", "antes": 5, "despues": 10}
    ]


def test_el_modelo_recibe_el_prompt_de_edicion_y_el_programa_previo(tmp_path, monkeypatch):
    """S9/S1: el sistema es `editor-v1` y el mensaje lleva el programa y la instrucción."""
    enviado: dict = {}

    def consultar_falso(cuerpo, **resto):
        enviado["cuerpo"] = cuerpo
        return {
            "model": "modelo-simulado",
            "choices": [{"message": {"content": json.dumps(_placa(10))}}],
        }

    monkeypatch.setenv("LLM_BASE_URL", "http://modelo-simulado-no-contactado")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(llm_resiliente, "consultar", consultar_falso)

    previo = _placa(5)
    resultado = pipeline.editar_pieza(previo, "hazla 5 mm más gruesa", directorio=tmp_path)

    cuerpo = enviado["cuerpo"]
    assert pipeline.PROMPT_EDICION.etiqueta == "editor-v1"
    assert cuerpo["messages"][0] == {
        "role": "system",
        "content": pipeline.PROMPT_EDICION.texto,
    }
    assert cuerpo["messages"][0]["content"] != pipeline.PROMPT_SISTEMA
    mensaje = cuerpo["messages"][1]["content"]
    assert cuerpo["messages"][1]["role"] == "user"
    assert json.dumps(previo, ensure_ascii=False, sort_keys=True) in mensaje
    assert "hazla 5 mm más gruesa" in mensaje
    assert resultado.programa["parts"][0]["params"]["thick"] == 10
    assert resultado.step.exists() and resultado.glb.exists()


def test_una_edicion_que_rompe_la_verificacion_declina_sin_construir(tmp_path):
    """AC2/S6: el verificador determinista es la red de seguridad de la edición."""
    previo = _placa(5)
    roto = _placa(-5)

    with pytest.raises(pipeline.ErrorVerificacion) as excinfo:
        pipeline.editar_pieza(
            previo,
            "hazla mucho más fina",
            planificar=lambda texto: roto,
            directorio=tmp_path,
        )

    assert excinfo.value.causa is declinacion.Causa.DIMENSION_INCOHERENTE
    assert not list(tmp_path.rglob("*.step"))
    assert not list(tmp_path.rglob("*.glb"))
    # El programa rechazado queda en disco para el diagnóstico, como en /generar.
    assert len(list(tmp_path.rglob("programa.json"))) == 1


def test_un_cambio_que_el_modelo_no_puede_expresar_declina(tmp_path):
    """S6/AC2: el rechazo honesto del modelo es una declinación con causa."""
    previo = _placa(5)

    with pytest.raises(pipeline.PiezaDeclinada) as excinfo:
        pipeline.editar_pieza(
            previo,
            "cámbiala por un engranaje",
            planificar=lambda texto: {"unsupported": "engranaje"},
            directorio=tmp_path,
        )

    assert excinfo.value.causa is declinacion.Causa.FAMILIA_NO_SOPORTADA
    assert excinfo.value.programa_json is not None
    assert not list(tmp_path.rglob("*.step"))
    assert not list(tmp_path.rglob("*.glb"))


@pytest.mark.parametrize(
    "instruccion",
    ["", "   ", "x" * 1001],
    ids=["vacia", "espacios", "demasiado-larga"],
)
def test_una_instruccion_invalida_no_llega_al_modelo(tmp_path, instruccion):
    """S1: la instrucción se valida como el texto de `/generar` (1..1000)."""
    llamado: list[str] = []

    def planificar(texto: str) -> dict:
        llamado.append(texto)
        return _espaciador()

    with pytest.raises(ValueError, match="entre 1 y 1000"):
        pipeline.editar_pieza(
            _espaciador(), instruccion, planificar=planificar, directorio=tmp_path
        )

    assert llamado == []
    assert list(tmp_path.iterdir()) == []


def test_el_programa_previo_no_se_modifica_al_editar(tmp_path):
    """S4: la edición no muta el programa del que parte."""
    previo = _espaciador(10)
    copia = json.loads(json.dumps(previo))

    pipeline.editar_pieza(
        previo,
        "hazla 5 mm más alta",
        planificar=lambda texto: _espaciador(15),
        directorio=tmp_path,
    )

    assert previo == copia
