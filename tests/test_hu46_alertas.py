"""Alertas de regresión de calidad (HU-46 / SPEC-047), sin red, key ni GPU."""

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from m2_cad import alertas

RAIZ = Path(__file__).resolve().parents[1]
FECHA = "20261127T120000Z"


def _registro(
    identificador: str,
    familia: str,
    esperado: str,
    correcto: bool,
    estado: str,
    causa: str = "ninguna",
) -> dict:
    return {
        "id": identificador,
        "familia": familia,
        "esperado": esperado,
        "correcto": correcto,
        "estado": estado,
        "causa": causa,
    }


def _escribir_corrida(tmp_path: Path, registros: list[dict], nombre: str) -> tuple[Path, Path]:
    resumen = tmp_path / f"{nombre}.json"
    csv_casos = tmp_path / f"{nombre}.csv"
    with csv_casos.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=alertas.CAMPOS_CSV)
        escritor.writeheader()
        escritor.writerows(registros)
    resumen.write_text(
        json.dumps(
            {
                "casos": len(registros),
                "acierto": sum(bool(r["correcto"]) for r in registros) / len(registros),
                "modo": "replay",
                "modelo": "deepseek-v4-pro",
                "prompt_version": "planner-v1",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return resumen, csv_casos


def _baseline(
    tmp_path: Path,
    registros: list[dict],
    *,
    umbrales: dict | None = None,
    nombre: str = "baseline.json",
) -> Path:
    resumen, csv_casos = _escribir_corrida(tmp_path, registros, "referencia")
    corrida = alertas.leer_corrida(resumen, csv_casos)
    datos = alertas.construir_baseline(
        corrida,
        autor="Juan Camilo Pérez",
        motivo="baseline inicial del replay de HU-44",
        corrida_origen="replay-20261127T120000Z",
        issue="#106",
        fecha=FECHA,
    )
    if umbrales is not None:
        datos["umbrales"] = umbrales
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(datos, indent=2), encoding="utf-8")
    return ruta


def _cli(*argumentos: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(RAIZ / "scripts" / "verificar_alertas.py"), *argumentos],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def registros_base() -> list[dict]:
    return [
        _registro("HU02-P01", "plate", "JSON", True, "construida"),
        _registro("HU02-P02", "plate", "JSON", True, "construida"),
        _registro(
            "HU02-N01", "fuera_alcance", "declinar", True, "declinada", "familia_no_soportada"
        ),
        _registro(
            "HU02-N02", "fuera_alcance", "declinar", True, "declinada", "familia_no_soportada"
        ),
    ]


def test_ac1_regresion_detectada_falla_y_lista_metricas_y_casos(tmp_path, registros_base):
    """AC1: una caída sobre el umbral falla y el resumen nombra métricas y casos."""
    baseline = _baseline(tmp_path, registros_base)
    degradada = [registros_base[0] | {"correcto": False}] + registros_base[1:]
    corrida_json, corrida_csv = _escribir_corrida(tmp_path, degradada, "corrida")
    salida = tmp_path / "alertas"

    ejecucion = _cli(
        "--corrida",
        str(corrida_json),
        "--csv",
        str(corrida_csv),
        "--baseline",
        str(baseline),
        "--salida",
        str(salida),
    )

    assert ejecucion.returncode == 1, ejecucion.stderr
    resultado = json.loads((salida / "ultimo.json").read_text(encoding="utf-8"))
    assert resultado["regresion"] is True
    assert set(resultado["degradadas"]) == {"acierto", "errores_silenciosos"}
    assert [caso["id"] for caso in resultado["casos_cambiados"]] == ["HU02-P01"]
    contenido = (salida / "ultimo.md").read_text(encoding="utf-8")
    assert "DEGRADADA" in contenido
    assert "HU02-P01" in contenido
    assert "plate" in contenido


def test_ac2_sin_regresion_sale_cero_y_no_emite_alerta(tmp_path, registros_base):
    """AC2: métricas dentro del umbral => código 0, sin Markdown y sin tocar el baseline."""
    baseline = _baseline(tmp_path, registros_base)
    antes = baseline.read_bytes()
    corrida_json, corrida_csv = _escribir_corrida(tmp_path, registros_base, "corrida")
    salida = tmp_path / "alertas"

    ejecucion = _cli(
        "--corrida",
        str(corrida_json),
        "--csv",
        str(corrida_csv),
        "--baseline",
        str(baseline),
        "--salida",
        str(salida),
    )

    assert ejecucion.returncode == 0, ejecucion.stderr
    assert json.loads((salida / "ultimo.json").read_text())["regresion"] is False
    assert not list(salida.glob("*.md"))
    assert baseline.read_bytes() == antes


def test_ac3_desglose_incluye_familia_y_causa_de_la_declinacion(tmp_path, registros_base):
    """AC3: el desglose muestra familia y etiqueta cerrada de SPEC-027."""
    baseline = _baseline(tmp_path, registros_base)
    degradada = [
        registros_base[0],
        registros_base[1],
        registros_base[2] | {"correcto": False, "estado": "construida", "causa": "ninguna"},
        registros_base[3],
    ]
    corrida_json, corrida_csv = _escribir_corrida(tmp_path, degradada, "corrida")
    salida = tmp_path / "alertas"

    ejecucion = _cli(
        "--corrida",
        str(corrida_json),
        "--csv",
        str(corrida_csv),
        "--baseline",
        str(baseline),
        "--salida",
        str(salida),
    )

    assert ejecucion.returncode == 1, ejecucion.stderr
    contenido = (salida / "ultimo.md").read_text(encoding="utf-8")
    assert "declinaciones correctas" in contenido
    assert "HU02-N01" in contenido
    assert "fuera_alcance" in contenido
    assert "familia_no_soportada → ninguna" in contenido


def test_ac4_actualizar_baseline_exige_y_registra_quien_cuando_y_desde_donde(
    tmp_path, registros_base
):
    """AC4: el cambio de referencia es explícito, trazable y append-only."""
    baseline = _baseline(tmp_path, registros_base)
    corrida_json, corrida_csv = _escribir_corrida(tmp_path, registros_base, "corrida")

    sin_autor = _cli(
        "--actualizar-baseline",
        "--corrida",
        str(corrida_json),
        "--csv",
        str(corrida_csv),
        "--baseline",
        str(baseline),
    )
    assert sin_autor.returncode == 2

    ejecucion = _cli(
        "--actualizar-baseline",
        "--corrida",
        str(corrida_json),
        "--csv",
        str(corrida_csv),
        "--baseline",
        str(baseline),
        "--autor",
        "Ana Revisora",
        "--motivo",
        "nueva referencia aprobada en la PR #106",
        "--corrida-origen",
        "mlflow-run-abc123",
        "--issue",
        "#106",
    )
    assert ejecucion.returncode == 0, ejecucion.stderr
    datos = json.loads(baseline.read_text(encoding="utf-8"))
    assert datos["actualizado"] == {
        "por": "Ana Revisora",
        "fecha": datos["actualizado"]["fecha"],
        "corrida": "mlflow-run-abc123",
        "motivo": "nueva referencia aprobada en la PR #106",
        "issue": "#106",
    }
    assert len(datos["historial"]) == 2
    assert datos["historial"][-1] == datos["actualizado"]


def test_umbrales_del_artefacto_versionado_se_respetan(tmp_path, registros_base):
    """RNF-3: una caída permitida por el baseline no genera alerta."""
    baseline = _baseline(
        tmp_path,
        registros_base,
        umbrales={"acierto": 0.3, "declinaciones_correctas": 1, "errores_silenciosos": 1},
    )
    degradada = [registros_base[0] | {"correcto": False}] + registros_base[1:]
    corrida_json, corrida_csv = _escribir_corrida(tmp_path, degradada, "corrida")
    corrida = alertas.leer_corrida(corrida_json, corrida_csv)

    resultado = alertas.comparar(alertas.cargar_baseline(baseline), corrida)
    assert resultado["regresion"] is False
    assert resultado["metrica"]["acierto"]["delta"] == pytest.approx(0.25)


def test_causa_fuera_del_catalogo_se_rechaza_antes_de_comparar(tmp_path, registros_base):
    """RF-3: no se aceptan etiquetas de causa inventadas como dimensión de métricas."""
    datos = registros_base[0] | {"causa": "fallo raro"}
    corrida_json, corrida_csv = _escribir_corrida(tmp_path, [datos] + registros_base[1:], "corrida")

    with pytest.raises(alertas.ErrorAlertas, match="catálogo de declinación"):
        alertas.leer_corrida(corrida_json, corrida_csv)


def test_corrida_incompleta_falla_con_codigo_2(tmp_path, registros_base):
    """Una corrida que no cubre los casos del baseline aborta sin generar alerta."""
    baseline = _baseline(tmp_path, registros_base)
    corrida_json, corrida_csv = _escribir_corrida(tmp_path, registros_base[:3], "corrida")
    salida = tmp_path / "alertas"

    ejecucion = _cli(
        "--corrida",
        str(corrida_json),
        "--csv",
        str(corrida_csv),
        "--baseline",
        str(baseline),
        "--salida",
        str(salida),
    )

    assert ejecucion.returncode == 2
    assert "no coinciden" in ejecucion.stdout
    assert not salida.exists()


def test_no_fail_publica_el_resultado_sin_fallar_el_workflow(tmp_path, registros_base):
    """RF-4: el workflow programado decide qué hacer con la regresión detectada."""
    baseline = _baseline(tmp_path, registros_base)
    degradada = [registros_base[0] | {"correcto": False}] + registros_base[1:]
    corrida_json, corrida_csv = _escribir_corrida(tmp_path, degradada, "corrida")
    salida = tmp_path / "alertas"

    ejecucion = _cli(
        "--no-fail",
        "--corrida",
        str(corrida_json),
        "--csv",
        str(corrida_csv),
        "--baseline",
        str(baseline),
        "--salida",
        str(salida),
    )

    assert ejecucion.returncode == 0, ejecucion.stderr
    resultado = json.loads((salida / "ultimo.json").read_text(encoding="utf-8"))
    assert resultado["codigo"] == 1
    assert resultado["regresion"] is True
    assert (salida / "ultimo.md").exists()
