"""Banco en replay con respuestas grabadas (HU-44 / SPEC-045), sin red ni tokens."""

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("cadquery")

from m2_cad import banco, banco_replay, dataset, llm_resiliente, pipeline  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _sin_seguimiento(monkeypatch):
    """Aísla estas pruebas de MLflow y de credenciales del entorno."""
    monkeypatch.setenv("MLFLOW_TRACKING_ENABLED", "0")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)


def _banco_y_filas(tmp_path: Path, ids: tuple[str, ...]) -> tuple[Path, list[dict]]:
    filas = [fila for fila in dataset.read_dataset() if fila["id"] in ids]
    assert len(filas) == len(ids)
    ruta = tmp_path / "banco.csv"
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=dataset.COLUMNS)
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta, filas


def _artefacto(tmp_path: Path, filas: list[dict]) -> Path:
    return banco_replay.escribir(banco_replay.sembrar(filas), tmp_path / "respuestas.json")


def test_clave_cuerpo_es_la_del_replay_y_no_depende_de_la_credencial(monkeypatch):
    """RF-2: la clave canónica de HU-25 es estable aunque cambie la API key."""
    solicitud = "Placa de 40 x 30 x 5 mm"
    cuerpo = pipeline.cuerpo_planificador(solicitud)
    antes = llm_resiliente.clave_cuerpo(cuerpo, banco_replay.URL_REPLAY)

    monkeypatch.setenv("DEEPSEEK_API_KEY", "clave-solo-local")
    despues = llm_resiliente.clave_cuerpo(cuerpo, banco_replay.URL_REPLAY)

    assert antes == despues == banco_replay.clave_de({"solicitud": solicitud})


def test_cargar_rechaza_un_prompt_distinto_del_vigente(tmp_path):
    """AC3: un artefacto con otra versión de prompt se rechaza antes de correr."""
    _, filas = _banco_y_filas(tmp_path, ("HU02-P01",))
    ruta = _artefacto(tmp_path, filas)
    assert banco_replay.cargar(ruta)["prompt"]["etiqueta"] == "planner-v1"

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["prompt"]["version"] = 2
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(banco_replay.ErrorReplay, match="prompt.version"):
        banco_replay.cargar(ruta)


def test_preparar_falla_si_falta_una_respuesta(tmp_path):
    """RNF-3: una grabación ausente aborta; nunca se sustituye por el modelo."""
    banco_csv, filas = _banco_y_filas(tmp_path, ("HU02-P01", "HU02-N01"))
    ruta = _artefacto(tmp_path, filas)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["respuestas"] = datos["respuestas"][:1]
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(banco_replay.ErrorReplay, match="HU02-N01"):
        banco_replay.preparar(dataset.read_dataset(banco_csv), ruta)


def test_ac1_replay_no_llama_al_modelo_y_gasta_cero_tokens(tmp_path, monkeypatch):
    """AC1: el pipeline real corre, el proveedor grabado no contacta la red."""
    banco_csv, filas = _banco_y_filas(tmp_path, ("HU02-P01", "HU02-N01"))
    ruta = _artefacto(tmp_path, filas)
    salida = tmp_path / "salida"

    def prohibido(*_args, **_kwargs):
        raise AssertionError("El replay no debe llamar al proveedor real")

    monkeypatch.setattr(pipeline.llm, "chat", prohibido)

    codigo = banco.main(
        [
            "--banco",
            str(banco_csv),
            "--respuestas",
            str(ruta),
            "--salida",
            str(salida),
            "--replay",
        ]
    )

    assert codigo == 0
    resumen = json.loads(next(salida.glob("*.json")).read_text(encoding="utf-8"))
    assert resumen["modo"] == "replay"
    assert resumen["prompt_version"] == "planner-v1"
    assert resumen["tokens_entrada"] == resumen["tokens_salida"] == 0
    assert resumen["acierto"] == 1.0


def test_ac1_bajo_el_umbral_el_banco_falla_y_deja_el_resumen(tmp_path, monkeypatch):
    """AC1: una caída de aceptación falla el job y queda evidencia del umbral."""
    banco_csv, filas = _banco_y_filas(tmp_path, ("HU02-P01",))
    ruta = _artefacto(tmp_path, filas)
    salida = tmp_path / "salida"
    original = banco.evaluar_caso

    def degradar(fila, **kwargs):
        registro = original(fila, **kwargs)
        registro["correcto"] = False
        return registro

    monkeypatch.setattr(banco, "evaluar_caso", degradar)

    codigo = banco.main(
        [
            "--banco",
            str(banco_csv),
            "--respuestas",
            str(ruta),
            "--salida",
            str(salida),
            "--umbral",
            "1.0",
            "--replay",
        ]
    )

    assert codigo == 1
    resumen = json.loads(next(salida.glob("*.json")).read_text(encoding="utf-8"))
    assert resumen["acierto"] == 0.0
    assert resumen["umbral"] == 1.0


def test_grabar_registra_el_prompt_y_el_origen_proveedor(tmp_path):
    """RF-2: la regrabación real declara versión de prompt y origen, sin red aquí."""
    _, filas = _banco_y_filas(tmp_path, ("HU02-P01",))
    contenido = json.dumps(banco_replay.programa_referencia(filas[0]))
    ruta = tmp_path / "grabado.json"

    def proveedor(cuerpo, *, url, timeout):
        return {
            "id": "simulado",
            "model": pipeline.llm.planner_model(),
            "choices": [{"message": {"role": "assistant", "content": contenido}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        }

    datos = banco_replay.grabar(
        filas, ruta=ruta, proveedor_real=proveedor, url="http://proveedor.invalid/v1"
    )

    assert datos["origen"] == "proveedor"
    assert datos["prompt"] == banco_replay.prompt_actual()
    assert banco_replay.cargar(ruta)["respuestas"][0]["prompt_version"] == "planner-v1"


def test_script_de_verificacion_acepta_el_artefacto(tmp_path):
    """RF-3: el mismo comando que corre CI valida esquema, prompt y cobertura."""
    banco_csv, filas = _banco_y_filas(tmp_path, ("HU02-P01", "HU02-N01"))
    ruta = _artefacto(tmp_path, filas)

    resultado = subprocess.run(
        [
            sys.executable,
            "-B",
            str(RAIZ / "scripts" / "verify_banco_replay.py"),
            "--banco",
            str(banco_csv),
            "--respuestas",
            str(ruta),
            "--solo-verificar",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "replay válido: 2 respuestas" in resultado.stdout
