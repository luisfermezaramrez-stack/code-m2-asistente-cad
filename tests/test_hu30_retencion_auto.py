"""SPEC-031 AC4: integración real con lifespan FastAPI y limpieza automática."""

import os
import time
import uuid

from fastapi.testclient import TestClient

from m2_cad import api


def _vencida(root):
    root.mkdir(exist_ok=True)
    carpeta = root / uuid.uuid4().hex
    carpeta.mkdir()
    archivo = carpeta / "pieza.step"
    archivo.write_text("STEP", encoding="utf-8")
    marca = time.time() - 10 * 86400
    os.utime(archivo, (marca, marca))
    os.utime(carpeta, (marca, marca))
    return carpeta


def test_limpieza_automatica_al_iniciar_api(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    antigua = _vencida(tmp_path / "outputs")
    monkeypatch.setenv("M2_OUTPUT_RETENTION_DAYS", "7")
    monkeypatch.setenv("M2_OUTPUT_SWEEP_SECONDS", "1")
    with TestClient(api.app) as cliente:
        assert cliente.get("/health").status_code == 200
        for _ in range(100):
            if not antigua.exists():
                break
            time.sleep(0.01)
        assert not antigua.exists()


def test_no_limpia_mientras_hay_generaciones_activas(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    antigua = _vencida(tmp_path / "outputs")
    monkeypatch.setenv("M2_OUTPUT_RETENTION_DAYS", "7")
    monkeypatch.setenv("M2_OUTPUT_SWEEP_SECONDS", "1")
    monkeypatch.setattr(api.gestor_trabajos, "hay_trabajos_activos", lambda: True)
    with TestClient(api.app) as cliente:
        assert cliente.get("/health").status_code == 200
        time.sleep(0.05)
        assert antigua.exists()
