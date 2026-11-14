"""HU-10 AC3/AC4: prueba de humo y latencia del despliegue; sin red ni modelo real."""

import csv
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

RUTA = Path(__file__).resolve().parents[1] / "scripts" / "smoke_deploy.py"
especificacion = importlib.util.spec_from_file_location("smoke_deploy", RUTA)
smoke = importlib.util.module_from_spec(especificacion)
especificacion.loader.exec_module(smoke)


def _transporte(fallar_en: str | None = None):
    """Simula /generar: pieza para los positivos, declinación para los negativos."""

    negativos = {f["solicitud"] for f in smoke.read_dataset() if f["familia"] == "fuera_alcance"}

    def responder(request: httpx.Request) -> httpx.Response:
        if request.url.path != "/generar":
            return httpx.Response(404)
        texto = json.loads(request.content)["texto"]
        if fallar_en and fallar_en == texto:
            return httpx.Response(503, json={"detail": "El modelo no está disponible."})
        if texto in negativos:
            return httpx.Response(422, json={"detail": "Pieza declinada: fuera del catálogo"})
        return httpx.Response(200, json={"step": "/salidas/pieza.step"})

    return httpx.MockTransport(responder)


def test_seleccion_alterna_familias_para_la_prueba_de_humo():
    # Arrange
    filas = smoke.read_dataset()

    # Act
    elegidas = smoke.seleccionar(filas, 5)

    # Assert
    assert [fila["familia"] for fila in elegidas] == [
        "plate",
        "sheet_bracket",
        "adapter",
        "flange",
        "spacer",
    ]


def test_seleccion_por_ids_respeta_el_orden_pedido():
    filas = smoke.read_dataset()

    elegidas = smoke.seleccionar(filas, 5, ids=["HU02-N01", "HU02-P02"])

    assert [fila["id"] for fila in elegidas] == ["HU02-N01", "HU02-P02"]


def test_seleccion_rechaza_id_inexistente():
    with pytest.raises(ValueError, match="HU02-X99"):
        smoke.seleccionar(smoke.read_dataset(), 5, ids=["HU02-X99"])


@pytest.mark.parametrize(
    ("valores", "p50", "p90"),
    [([1.0], 1.0, 1.0), ([3.0, 1.0, 2.0, 4.0], 2.0, 4.0), (list(range(1, 11)), 5, 9)],
)
def test_percentiles_por_rango_mas_cercano(valores, p50, p90):
    assert smoke.percentil(valores, 50) == p50
    assert smoke.percentil(valores, 90) == p90


def test_humo_exitoso_escribe_csv_y_resumen(tmp_path, capsys):
    # Arrange
    argv = ["--n", "7", "--salida", str(tmp_path)]

    # Act
    codigo = smoke.main(argv, transport=_transporte())

    # Assert
    assert codigo == 0
    with (tmp_path / "smoke.csv").open(encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    assert [fila["familia"] for fila in filas][-1] == "fuera_alcance"
    assert {fila["resultado"] for fila in filas} == {"pieza", "declinada"}
    assert all(float(fila["latencia_s"]) >= 0 for fila in filas)
    resumen = json.loads((tmp_path / "smoke.json").read_text(encoding="utf-8"))
    assert resumen["n"] == 7 and resumen["validas"] == 7
    assert resumen["p50_s"] <= resumen["p90_s"]
    assert "7/7" in capsys.readouterr().out


def test_humo_con_un_fallo_devuelve_codigo_1(tmp_path):
    fila = smoke.seleccionar(smoke.read_dataset(), 2)[1]

    codigo = smoke.main(
        ["--n", "2", "--salida", str(tmp_path)], transport=_transporte(fila["solicitud"])
    )

    assert codigo == 1
    resumen = json.loads((tmp_path / "smoke.json").read_text(encoding="utf-8"))
    assert resumen["validas"] == 1
    with (tmp_path / "smoke.csv").open(encoding="utf-8") as archivo:
        fallida = list(csv.DictReader(archivo))[1]
    assert fallida["estado_http"] == "503" and fallida["resultado"] == "error"


def test_un_422_de_validacion_no_cuenta_como_declinacion(tmp_path):
    transporte = httpx.MockTransport(
        lambda request: httpx.Response(422, json={"detail": [{"msg": "texto vacío"}]})
    )

    codigo = smoke.main(["--n", "1", "--salida", str(tmp_path)], transport=transporte)

    assert codigo == 1
