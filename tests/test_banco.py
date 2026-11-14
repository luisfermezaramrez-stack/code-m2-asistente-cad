"""Runner del banco HU-02 contra el modelo (HU-14, AC6 y AC7), con el modelo simulado."""

import csv
import json
from pathlib import Path

import pytest

pytest.importorskip("cadquery")

from m2_cad import banco, pipeline  # noqa: E402

FILA_PLACA = {
    "id": "HU02-P01",
    "familia": "plate",
    "solicitud": "Placa de 40 x 30 x 5 mm",
    "medidas": "{}",
    "resultado_esperado": json.dumps({"volumen_mm3": 6000.0, "caja_xyz_mm": [40.0, 30.0, 5.0]}),
}
FILA_NEGATIVA = {
    "id": "HU02-N01",
    "familia": "fuera_alcance",
    "solicitud": "Calcula una viga",
    "medidas": "{}",
    "resultado_esperado": "declinar",
}


def _resultado(volumen: float, caja: tuple[float, float, float]) -> pipeline.ResultadoPieza:
    return pipeline.ResultadoPieza(
        programa={},
        step=Path("p.step"),
        glb=Path("p.glb"),
        bom_csv=Path("p.csv"),
        volumen_mm3=volumen,
        caja_mm=caja,
        tiempo_construccion_s=0.1,
    )


def _fallar(error: Exception):
    def generar(texto: str, directorio: Path):
        raise error

    return generar


@pytest.mark.parametrize(
    ("fila", "generar", "estado", "correcto"),
    [
        pytest.param(
            FILA_PLACA,
            lambda texto, directorio: _resultado(6050.0, (40.2, 30.0, 5.0)),
            "construida",
            True,
            id="dentro-de-2-por-ciento",
        ),
        pytest.param(
            FILA_PLACA,
            lambda texto, directorio: _resultado(7000.0, (40.0, 30.0, 5.0)),
            "construida",
            False,
            id="volumen-fuera-de-tolerancia",
        ),
        pytest.param(
            FILA_PLACA,
            _fallar(pipeline.ErrorVerificacion("unknown param")),
            "invalido",
            False,
            id="no-pasa-dsl-check",
        ),
        pytest.param(
            FILA_PLACA,
            _fallar(pipeline.ErrorGeneracion("sin JSON")),
            "sin_programa",
            False,
            id="sin-programa",
        ),
        pytest.param(
            FILA_NEGATIVA,
            _fallar(pipeline.PiezaDeclinada("fuera del catálogo")),
            "declinada",
            True,
            id="negativo-declinado",
        ),
        pytest.param(
            FILA_NEGATIVA,
            lambda texto, directorio: _resultado(1.0, (1.0, 1.0, 1.0)),
            "construida",
            False,
            id="negativo-construido-por-error",
        ),
        pytest.param(
            FILA_PLACA,
            _fallar(ValueError("bd_warehouse: size")),
            "error_construccion",
            False,
            id="error-del-kernel",
        ),
    ],
)
def test_evaluar_caso(tmp_path, fila, generar, estado, correcto):
    """AC7: cada caso queda clasificado y se compara con la referencia del banco (±2 %)."""
    registro = banco.evaluar_caso(fila, generar=generar, directorio=tmp_path)

    assert registro["estado"] == estado
    assert registro["correcto"] is correcto
    assert registro["id"] == fila["id"]


def test_modelo_no_disponible_detiene_el_banco(tmp_path):
    """AC3: sin modelo no se sigue gastando ni se cuentan fallos falsos."""
    with pytest.raises(pipeline.ModeloNoDisponible):
        banco.evaluar_caso(
            FILA_PLACA,
            generar=_fallar(pipeline.ModeloNoDisponible("falta DEEPSEEK_API_KEY")),
            directorio=tmp_path,
        )


def test_resumir_calcula_tasas_latencia_tokens_y_costo():
    """AC7: resumen con acierto, tasa de /dsl/check, latencia, tokens y costo estimado."""
    registros = [
        {
            "estado": "construida",
            "correcto": True,
            "latencia_s": 2.0,
            "tokens_entrada": 1000,
            "tokens_salida": 100,
        },
        {
            "estado": "declinada",
            "correcto": True,
            "latencia_s": 4.0,
            "tokens_entrada": 1000,
            "tokens_salida": 100,
        },
        {
            "estado": "invalido",
            "correcto": False,
            "latencia_s": 6.0,
            "tokens_entrada": 2000,
            "tokens_salida": 200,
        },
        {
            "estado": "sin_programa",
            "correcto": False,
            "latencia_s": 0.0,
            "tokens_entrada": 0,
            "tokens_salida": 0,
        },
    ]

    resumen = banco.resumir(registros, precio_entrada=2.0, precio_salida=4.0)

    assert resumen["casos"] == 4
    assert resumen["acierto"] == pytest.approx(0.5)
    assert resumen["tasa_dsl_check"] == pytest.approx(0.5)
    assert resumen["latencia_media_s"] == pytest.approx(3.0)
    assert resumen["tokens_entrada"] == 4000
    assert resumen["tokens_salida"] == 400
    assert resumen["costo_usd"] == pytest.approx(4000 * 2.0 / 1e6 + 400 * 4.0 / 1e6)


def test_contador_de_uso_suma_tokens_de_la_respuesta():
    """AC7: los tokens salen del campo usage de la respuesta compatible con OpenAI."""

    def chat(cuerpo, *, url, timeout):
        return {"usage": {"prompt_tokens": 120, "completion_tokens": 30}, "choices": []}

    contador = banco.ContadorUso(chat)
    contador({}, url="u", timeout=1)
    contador({}, url="u", timeout=1)

    assert (contador.entrada, contador.salida) == (240, 60)


def test_main_escribe_csv_y_resumen(tmp_path, monkeypatch, capsys):
    """AC7: el comando deja un CSV por caso y un resumen JSON, sin red (modelo simulado)."""
    banco_csv = tmp_path / "banco.csv"
    with banco_csv.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(FILA_PLACA))
        escritor.writeheader()
        escritor.writerows([FILA_PLACA, FILA_NEGATIVA])

    def generar(texto, *, directorio):
        if texto == FILA_NEGATIVA["solicitud"]:
            raise pipeline.PiezaDeclinada("fuera del catálogo")
        return _resultado(6000.0, (40.0, 30.0, 5.0))

    monkeypatch.setattr(banco.pipeline, "generar_pieza", generar)
    salida = tmp_path / "salida"

    codigo = banco.main(
        ["--banco", str(banco_csv), "--salida", str(salida), "--ids", "HU02-P01,HU02-N01"]
    )

    assert codigo == 0
    filas = list(csv.DictReader(next(salida.glob("*.csv")).open(encoding="utf-8")))
    assert [fila["estado"] for fila in filas] == ["construida", "declinada"]
    resumen = json.loads(next(salida.glob("*.json")).read_text(encoding="utf-8"))
    assert resumen["acierto"] == 1.0
    assert "acierto" in capsys.readouterr().out


def test_main_sin_api_key_termina_con_mensaje_en_espanol(tmp_path, monkeypatch, capsys):
    """AC3: sin DEEPSEEK_API_KEY el banco termina con código 2 y no escribe resultados."""
    for variable in ("LLM_BASE_URL", "PLANNER_URL", "QWEN_BASE_URL", "LLM_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    salida = tmp_path / "salida"

    codigo = banco.main(["--salida", str(salida), "--ids", "HU02-P01"])

    assert codigo == 2
    assert "falta DEEPSEEK_API_KEY" in capsys.readouterr().out
    assert not salida.exists()
