"""SPEC-031 AC4: retención segura y automática sin red, GPU ni CAD."""

import os
import time
import uuid

import pytest

from m2_cad.retencion_salidas import depurar_outputs, leer_politica


def _carpeta(raiz, *, edad_dias, nombre=None):
    ruta = raiz / (nombre or uuid.uuid4().hex)
    ruta.mkdir()
    archivo = ruta / "pieza.step"
    archivo.write_text("STEP SIMULADO", encoding="utf-8")
    marca = time.time() - edad_dias * 86400
    os.utime(archivo, (marca, marca))
    os.utime(ruta, (marca, marca))
    return ruta


def test_ac4_elimina_vencidos_y_conserva_vigentes(tmp_path):
    raiz = tmp_path / "outputs"
    raiz.mkdir()
    antiguo = _carpeta(raiz, edad_dias=8)
    reciente = _carpeta(raiz, edad_dias=1)
    borrados = depurar_outputs(raiz, dias=7)
    assert borrados == [antiguo]
    assert not antiguo.exists()
    assert (reciente / "pieza.step").is_file()


def test_ac4_no_borra_carpetas_ajenas_o_archivos_sueltos(tmp_path):
    raiz = tmp_path / "outputs"
    raiz.mkdir()
    ajena = _carpeta(raiz, edad_dias=90, nombre="archivos_manual")
    suelto = raiz / "registro.csv"
    suelto.write_text("no borrar", encoding="utf-8")
    assert depurar_outputs(raiz, dias=7) == []
    assert ajena.exists() and suelto.is_file()


def test_ac4_no_sigue_enlaces_simbolicos(tmp_path):
    raiz = tmp_path / "outputs"
    raiz.mkdir()
    externo = tmp_path / "externo"
    externo.mkdir()
    (externo / "intacto.step").write_text("intacto", encoding="utf-8")
    (raiz / uuid.uuid4().hex).symlink_to(externo, target_is_directory=True)
    assert depurar_outputs(raiz, dias=1) == []
    assert (externo / "intacto.step").exists()


def test_ac4_no_borra_directorio_con_enlace_interno(tmp_path):
    raiz = tmp_path / "outputs"
    raiz.mkdir()
    candidato = _carpeta(raiz, edad_dias=90)
    (candidato / "atajo").symlink_to(tmp_path, target_is_directory=True)
    assert depurar_outputs(raiz, dias=7) == []
    assert candidato.is_dir()


def test_ac4_archivo_reciente_protege_carpeta_antigua(tmp_path):
    raiz = tmp_path / "outputs"
    raiz.mkdir()
    candidato = _carpeta(raiz, edad_dias=90)
    (candidato / "en_proceso.txt").write_text("activo", encoding="utf-8")
    assert depurar_outputs(raiz, dias=7) == []
    assert candidato.exists()


def test_ac4_rechaza_retencion_invalida(tmp_path):
    with pytest.raises(ValueError):
        depurar_outputs(tmp_path, dias=0)
    with pytest.raises(ValueError):
        depurar_outputs(tmp_path, dias=-1)


def test_ac4_configuracion_y_desactivacion(monkeypatch):
    monkeypatch.delenv("M2_OUTPUT_RETENTION_DAYS", raising=False)
    assert leer_politica() is None
    monkeypatch.setenv("M2_OUTPUT_RETENTION_DAYS", "7")
    monkeypatch.setenv("M2_OUTPUT_SWEEP_SECONDS", "60")
    politica = leer_politica()
    assert politica is not None
    assert politica.dias == 7
    assert politica.intervalo_segundos == 60
    monkeypatch.setenv("M2_OUTPUT_RETENTION_DAYS", "nan")
    with pytest.raises(ValueError):
        leer_politica()


def test_ac4_directorio_no_existe_no_es_error(tmp_path):
    assert depurar_outputs(tmp_path / "outputs", dias=1) == []
