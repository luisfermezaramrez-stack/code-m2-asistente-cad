"""Seguimiento MLflow del banco HU-02 (specs/009-hu-16-mlflow: AC4, AC7).

Corre offline contra un file store temporal: una corrida padre por modelo con el
resumen y una hija por caso, comparables entre modelos sin abrir el CSV.
"""

import csv
import json
from pathlib import Path

import pytest

pytest.importorskip("cadquery")

from m2_cad import banco, pipeline, seguimiento  # noqa: E402

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


@pytest.fixture(autouse=True)
def _mlflow_temporal(tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")
    monkeypatch.setenv("MLFLOW_TRACKING_ENABLED", "1")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file:{tmp_path / 'mlruns'}")


def _corridas(tmp_path):
    from mlflow.tracking import MlflowClient

    cliente = MlflowClient(tracking_uri=f"file:{tmp_path / 'mlruns'}")
    experimento = cliente.get_experiment_by_name(seguimiento.EXPERIMENTO_BANCO)
    assert experimento is not None, "el banco no abrió su experimento"
    return cliente.search_runs([experimento.experiment_id])


def _correr_banco(tmp_path, monkeypatch):
    banco_csv = tmp_path / "banco.csv"
    with banco_csv.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(FILA_PLACA))
        escritor.writeheader()
        escritor.writerows([FILA_PLACA, FILA_NEGATIVA])

    def generar(texto, *, directorio):
        if texto == FILA_NEGATIVA["solicitud"]:
            raise pipeline.PiezaDeclinada("fuera del catálogo")
        return pipeline.ResultadoPieza(
            programa={},
            step=Path("p.step"),
            glb=Path("p.glb"),
            bom_csv=Path("p.csv"),
            volumen_mm3=6000.0,
            caja_mm=(40.0, 30.0, 5.0),
            tiempo_construccion_s=0.1,
        )

    monkeypatch.setattr(banco.pipeline, "generar_pieza", generar)
    codigo = banco.main(
        [
            "--banco",
            str(banco_csv),
            "--salida",
            str(tmp_path / "salida"),
            "--ids",
            "HU02-P01,HU02-N01",
        ]
    )
    assert codigo == 0
    return _corridas(tmp_path)


def test_banco_registra_corrida_padre_con_el_resumen(tmp_path, monkeypatch):
    """AC4: el resumen (acierto, latencia media, tokens y costo) queda en la padre."""
    corridas = _correr_banco(tmp_path, monkeypatch)

    padres = [c for c in corridas if "caso" not in c.data.params]
    assert len(padres) == 1
    padre = padres[0]
    assert padre.info.status == "FINISHED"
    assert padre.data.params["modelo"] == pipeline.llm.planner_model()
    assert padre.data.params["n_casos"] == "2"
    assert padre.data.params["precio_entrada"] == "0.0"
    assert padre.data.tags["version_modelo"] == seguimiento.version_modelo()
    assert padre.data.metrics["acierto"] == pytest.approx(1.0)
    assert padre.data.metrics["acierto_positivas"] == pytest.approx(1.0)
    assert padre.data.metrics["acierto_negativas"] == pytest.approx(1.0)
    assert padre.data.metrics["dsl_check_ok_total"] == pytest.approx(2.0)
    assert "latencia_media_s" in padre.data.metrics
    assert "tokens_entrada" in padre.data.metrics
    assert "costo_usd" in padre.data.metrics


def test_banco_registra_una_corrida_hija_por_caso(tmp_path, monkeypatch):
    """AC4: cada caso deja acierto, dsl_check_ok y error_relativo_pct."""
    corridas = _correr_banco(tmp_path, monkeypatch)

    hijas = {c.data.params["caso"]: c for c in corridas if "caso" in c.data.params}
    assert sorted(hijas) == ["HU02-N01", "HU02-P01"]
    assert all(c.info.status == "FINISHED" for c in hijas.values())

    positiva = hijas["HU02-P01"]
    assert positiva.data.metrics["acierto"] == pytest.approx(1.0)
    assert positiva.data.metrics["dsl_check_ok"] == pytest.approx(1.0)
    assert positiva.data.metrics["error_relativo_pct"] == pytest.approx(0.0)

    negativa = hijas["HU02-N01"]
    assert negativa.data.tags["estado"] == "declinada"
    assert negativa.data.metrics["acierto"] == pytest.approx(1.0)
    assert "error_relativo_pct" not in negativa.data.metrics


def test_banco_registra_la_version_del_modelo_servido(tmp_path, monkeypatch):
    """AC7: la configuración servida queda como versión de modelo ligada a la corrida."""
    from mlflow.tracking import MlflowClient

    _correr_banco(tmp_path, monkeypatch)
    cliente = MlflowClient(tracking_uri=f"file:{tmp_path / 'mlruns'}")
    nombre = seguimiento.nombre_modelo_registrado(f"m2-cad-{pipeline.llm.planner_model()}")

    versiones = cliente.search_model_versions(f"name='{nombre}'")

    assert [version.tags["version_modelo"] for version in versiones] == [
        seguimiento.version_modelo()
    ]


def test_banco_interrumpido_no_deja_la_corrida_padre_en_running(tmp_path, monkeypatch):
    """AC4/AC3: una interrupción del banco cierra la corrida padre con estado=error."""
    banco_csv = tmp_path / "banco.csv"
    with banco_csv.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(FILA_PLACA))
        escritor.writeheader()
        escritor.writerow(FILA_PLACA)

    def interrumpir(texto, *, directorio):
        raise KeyboardInterrupt

    monkeypatch.setattr(banco.pipeline, "generar_pieza", interrumpir)
    with pytest.raises(KeyboardInterrupt):
        banco.main(["--banco", str(banco_csv), "--salida", str(tmp_path / "salida")])

    corridas = _corridas(tmp_path)
    assert [corrida.info.status for corrida in corridas] == ["FINISHED"]
    assert corridas[0].data.tags["estado"] == "error"
    assert corridas[0].data.tags["error"] == "KeyboardInterrupt"


def test_interrupcion_restaura_el_chat_del_pipeline(tmp_path, monkeypatch):
    """AC3: la interrupción cierra la corrida sin dejar el contador de uso activo."""
    banco_csv = tmp_path / "banco.csv"
    with banco_csv.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(FILA_PLACA))
        escritor.writeheader()
        escritor.writerow(FILA_PLACA)

    original = banco.pipeline.llm.chat
    monkeypatch.setattr(
        banco.pipeline,
        "generar_pieza",
        lambda texto, *, directorio: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    with pytest.raises(KeyboardInterrupt):
        banco.main(["--banco", str(banco_csv), "--salida", str(tmp_path / "salida")])

    assert banco.pipeline.llm.chat is original
