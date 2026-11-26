"""Corpus dorado del núcleo determinista (HU-23, SPEC-024).

Las pruebas de AC1, AC2 y AC4 construyen piezas reales, igual que `tests/test_pipeline.py`,
así que se saltan si el kernel CAD no está instalado. Las de esquema no lo necesitan.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from m2_cad import corpus_dorado, dataset

RAIZ = Path(__file__).resolve().parents[1]
RUNNER = RAIZ / "scripts" / "verify_corpus_dorado.py"


def _requiere_cad() -> None:
    pytest.importorskip("cadquery")


def _corpus_minimo(tmp_path: Path, mutar=lambda casos: None) -> Path:
    """Corpus de prueba con un caso aceptado y uno declinado, sacado del versionado.

    Las alteraciones deliberadas de AC1 y AC2 se prueban sobre esta copia temporal
    (supuesto de la spec), no sobre el corpus completo: cada caso construye una pieza.
    """
    datos = json.loads(corpus_dorado.DEFAULT_PATH.read_text(encoding="utf-8"))
    aceptado = next(caso for caso in datos["casos"] if caso["resultado"] == "acepta")
    declinado = next(caso for caso in datos["casos"] if caso["resultado"] == "declina")
    datos["casos"] = [aceptado, declinado]
    mutar(datos["casos"])
    ruta = tmp_path / "corpus.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


def _aceptados(casos: list[dict]) -> list[dict]:
    return [caso for caso in casos if caso["resultado"] == "acepta"]


# ---- Normalización del STEP: sólo lo que varía entre corridas (plan.md §1.1) ----

STEP_A = """ISO-10303-21;
HEADER;
FILE_NAME('Open CASCADE Shape Model','2026-11-24T23:09:10',('Author'),(
  'Open CASCADE'),'Open CASCADE STEP processor 7.8','Open CASCADE 7.8'
 ,'Unknown');
ENDSEC;
DATA;
#7 = PRODUCT('f79bcf46-e885-11f1-929f-d8bbc11f0e6f',
  'f79bcf46-e885-11f1-929f-d8bbc11f0e6f','',(#8));
#10 = CARTESIAN_POINT('',(0.,0.,0.));
#232 = NEXT_ASSEMBLY_USAGE_OCCURRENCE('1','p','',#5,#27,$);
ENDSEC;
END-ISO-10303-21;
"""


def test_normalizar_no_oculta_geometria():
    """La huella distingue cualquier cambio de geometría, no sólo los tres campos."""
    otra = STEP_A.replace("CARTESIAN_POINT('',(0.,0.,0.))", "CARTESIAN_POINT('',(0.5,0.,0.))")

    assert corpus_dorado.normalizar_step(STEP_A) != corpus_dorado.normalizar_step(otra)


def test_normalizar_neutraliza_marca_tiempo_guid_y_contador():
    """Las tres variaciones medidas entre dos corridas del mismo programa."""
    otra = (
        STEP_A.replace("2026-11-24T23:09:10", "2026-11-25T08:15:42")
        .replace("f79bcf46-e885-11f1-929f-d8bbc11f0e6f", "f7a2cda1-e885-11f1-b183-d8bbc11f0e6f")
        .replace("NEXT_ASSEMBLY_USAGE_OCCURRENCE('1'", "NEXT_ASSEMBLY_USAGE_OCCURRENCE('2'")
    )

    assert corpus_dorado.normalizar_step(STEP_A) == corpus_dorado.normalizar_step(otra)


# ---- Esquema: un caso sin resultado declarado es un error (AC3, RF-2) ----


def test_caso_sin_resultado_declarado_se_rechaza(tmp_path):
    with pytest.raises(corpus_dorado.ErrorCorpus, match="no declara resultado"):
        corpus_dorado.cargar_corpus(
            _corpus_minimo(tmp_path, lambda casos: casos[0].pop("resultado"))
        )


def test_resultado_desconocido_se_rechaza(tmp_path):
    def mutar(casos):
        casos[0]["resultado"] = "quizas"

    with pytest.raises(corpus_dorado.ErrorCorpus, match="«quizas»"):
        corpus_dorado.cargar_corpus(_corpus_minimo(tmp_path, mutar))


def test_caso_aceptado_sin_huella_se_rechaza_al_verificar(tmp_path):
    def mutar(casos):
        _aceptados(casos)[0].pop("sha256")

    with pytest.raises(corpus_dorado.ErrorCorpus, match="necesita una huella"):
        corpus_dorado.cargar_corpus(_corpus_minimo(tmp_path, mutar))


def test_caso_declinado_no_puede_congelar_huella(tmp_path):
    def mutar(casos):
        declinado = next(c for c in casos if c["resultado"] == "declina")
        declinado["sha256"] = "0" * 64

    with pytest.raises(corpus_dorado.ErrorCorpus, match="no puede congelar"):
        corpus_dorado.cargar_corpus(_corpus_minimo(tmp_path, mutar))


def test_caso_necesita_fuente_o_programa_pero_no_los_dos(tmp_path):
    def mutar(casos):
        casos[0]["programa"] = {"parts": []}

    with pytest.raises(corpus_dorado.ErrorCorpus, match="nunca los dos ni ninguno"):
        corpus_dorado.cargar_corpus(_corpus_minimo(tmp_path, mutar))


def test_fila_del_banco_sin_programa_se_rechaza_con_mensaje_claro(tmp_path):
    """Una fila negativa del banco no tiene parámetros: el programa va explícito."""

    def mutar(casos):
        declinado = next(c for c in casos if c["resultado"] == "declina")
        declinado.pop("programa")
        declinado["fuente"] = "HU02-N01"

    casos = corpus_dorado.cargar_corpus(_corpus_minimo(tmp_path, mutar))
    declinado = next(caso for caso in casos if caso["resultado"] == "declina")
    with pytest.raises(corpus_dorado.ErrorCorpus, match="no tiene programa"):
        corpus_dorado.programa_de_caso(declinado)


def test_id_repetido_se_rechaza(tmp_path):
    def mutar(casos):
        casos[1]["id"] = casos[0]["id"]

    with pytest.raises(corpus_dorado.ErrorCorpus, match="está repetido"):
        corpus_dorado.cargar_corpus(_corpus_minimo(tmp_path, mutar))


def test_fuente_inexistente_se_rechaza(tmp_path):
    def mutar(casos):
        _aceptados(casos)[0]["fuente"] = "HU02-P99"

    with pytest.raises(corpus_dorado.ErrorCorpus, match="HU02-P99"):
        corpus_dorado.cargar_corpus(_corpus_minimo(tmp_path, mutar))


def test_corpus_versionado_cubre_las_seis_familias():
    """RF-1: el corpus versionado cubre las seis familias del catálogo y declina."""
    casos = corpus_dorado.cargar_corpus()
    familias = set()
    for caso in casos:
        if "fuente" in caso:
            filas = {fila["id"]: fila for fila in dataset.read_dataset()}
            familias.add(json.loads(filas[caso["fuente"]]["medidas"])["tipo_motor"])

    assert familias == {"plate", "sheet_bracket", "adapter", "flange", "spacer", "screw"}
    assert any(caso["resultado"] == "declina" for caso in casos)


# ---- AC1, AC2 y AC4: comparación contra lo congelado ----


def test_huella_alterada_nombra_caso_esperado_y_obtenido(tmp_path):
    """AC1: una huella alterada a propósito nombra el caso y las dos huellas."""
    _requiere_cad()
    esperada = "f" * 64

    def mutar(casos):
        _aceptados(casos)[0]["sha256"] = esperada

    casos = corpus_dorado.cargar_corpus(_corpus_minimo(tmp_path, mutar))
    divergencias = corpus_dorado.comparar(casos, tmp_path)

    assert len(divergencias) == 1
    assert divergencias[0]["id"] == casos[0]["id"]
    obtenida = divergencias[0]["obtenido"]["sha256"]
    assert obtenida and obtenida != esperada
    descripcion = corpus_dorado.describir(divergencias[0])
    assert casos[0]["id"] in descripcion
    assert esperada in descripcion and obtenida in descripcion


def test_resultado_invertido_nombra_caso_esperado_y_obtenido(tmp_path):
    """AC2: invertir el resultado esperado nombra el caso y ambos resultados."""
    _requiere_cad()

    def aceptar_declarado(casos):
        declinado = next(c for c in casos if c["resultado"] == "declina")
        declinado["resultado"] = "acepta"
        declinado["sha256"] = "f" * 64

    def declinar_declarado(casos):
        aceptado = _aceptados(casos)[0]
        aceptado["resultado"] = "declina"
        aceptado.pop("sha256")

    for mutar, esperado, obtenido in (
        (aceptar_declarado, "acepta", "declina"),
        (declinar_declarado, "declina", "acepta"),
    ):
        casos = corpus_dorado.cargar_corpus(_corpus_minimo(tmp_path, mutar))
        divergencias = corpus_dorado.comparar(casos, tmp_path)

        assert len(divergencias) == 1
        descripcion = corpus_dorado.describir(divergencias[0])
        assert divergencias[0]["id"] in descripcion
        assert f"se esperaba {esperado}" in descripcion
        assert f"devolvió {obtenido}" in descripcion


def test_runner_sale_cero_sin_divergencias_y_uno_con_divergencia(tmp_path):
    """AC4 y AC1 a través del script: el código de salida es la señal de CI."""
    _requiere_cad()
    sin_cambios = subprocess.run(
        [sys.executable, "-B", str(RUNNER)], capture_output=True, text=True, check=False
    )
    assert sin_cambios.returncode == 0, sin_cambios.stderr

    def mutar(casos):
        _aceptados(casos)[0]["sha256"] = "f" * 64

    alterado = _corpus_minimo(tmp_path, mutar)
    con_divergencia = subprocess.run(
        [sys.executable, "-B", str(RUNNER), "--corpus", str(alterado)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert con_divergencia.returncode == 1
    assert "huella del STEP distinta" in con_divergencia.stderr


def test_write_congela_lo_observado_y_es_idempotente(tmp_path):
    """RF-5: `--write` regenera la huella, conserva ids y una segunda corrida no cambia nada."""
    _requiere_cad()
    alterada = _corpus_minimo(tmp_path, lambda casos: casos[0].update({"sha256": "f" * 64}))
    orden_original = [
        caso["id"] for caso in json.loads(alterada.read_text(encoding="utf-8"))["casos"]
    ]

    def regenerar() -> None:
        corrida = subprocess.run(
            [sys.executable, "-B", str(RUNNER), "--corpus", str(alterada), "--write"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert corrida.returncode == 0, corrida.stderr

    regenerar()
    congelado = alterada.read_text(encoding="utf-8")
    assert "f" * 64 not in congelado
    assert [caso["id"] for caso in json.loads(congelado)["casos"]] == orden_original
    casos = corpus_dorado.cargar_corpus(alterada)  # el resultado queda congelado y válido
    assert corpus_dorado.comparar(casos, tmp_path) == []

    regenerar()
    assert alterada.read_text(encoding="utf-8") == congelado


def test_runner_rechaza_corpus_invalido_con_exit_dos(tmp_path):
    """S2 y S11 a través del script: un caso sin resultado es error de corpus, no divergencia."""
    sin_resultado = _corpus_minimo(tmp_path, lambda casos: casos[0].pop("resultado"))
    corrida = subprocess.run(
        [sys.executable, "-B", str(RUNNER), "--corpus", str(sin_resultado)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert corrida.returncode == 2
    assert "no declara resultado" in corrida.stderr
    assert "acepta-plate-hu02-p01" in corrida.stderr
