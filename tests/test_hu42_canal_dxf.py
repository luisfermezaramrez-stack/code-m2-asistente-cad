"""SPEC-043 AC3 (RF-4): descarga del DXF por el canal de artefactos de SPEC-037.

Reutiliza el patrón de `tests/test_hu36_integracion.py` (sin motor CAD ni LLM)
y comprueba la no regresión de STEP/GLB/CSV (RNF-3 a nivel HTTP).
"""

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from m2_cad import api
from m2_cad.autenticacion import ANONIMO
from m2_cad.seguridad_descargas import emitir_token


class GestorConArtefactos:
    """Doble queScrève todos los artefactos de una generación verificada."""

    def __init__(self, artefactos: dict[str, Path]):
        self.artefactos = artefactos
        self.estado_actual = "verificado"
        self.consultas = 0

    def estado_vuelve(self, nuevo_estado: str) -> None:
        self.estado_actual = nuevo_estado

    def obtener(self, solicitud_id: str):
        self.consultas += 1
        return SimpleNamespace(
            usuario=ANONIMO,
            estado=lambda: {
                "estado": self.estado_actual,
                "resultado": {nombre: str(ruta) for nombre, ruta in self.artefactos.items()},
            },
        )


@pytest.fixture
def escenario_dxf(tmp_path, monkeypatch):
    """Canal de artefactos con STEP, GLB, CSV y DXF sobre el directorio de salidas."""
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", "s" * 64)
    monkeypatch.setenv("M2_DOWNLOAD_TTL_SECONDS", "60")
    carpeta = tmp_path / "outputs"
    carpeta.mkdir()
    ruta = lambda nombre: carpeta / f"pieza.{nombre}"  # noqa: E731
    artefactos = {}
    for nombre, contenido in (
        ("step", "STEPO_SIMULADO"),
        ("glb", b"glTF_SIMULADO"),
        ("csv", "material,cantidad\nsteel,1\n"),
        ("dxf", "DXF_SIMULADO"),
    ):
        archivo = ruta(nombre)
        archivo.write_bytes(contenido if isinstance(contenido, bytes) else contenido.encode())
        artefactos["bom_csv" if nombre == "csv" else nombre] = archivo
    gestor = GestorConArtefactos(artefactos)
    previo = dict(api.app.dependency_overrides)
    api.app.dependency_overrides[api.obtener_gestor_trabajos] = lambda: gestor
    api.app.dependency_overrides[api.obtener_directorio_salidas] = lambda: carpeta
    id_ = uuid.uuid4().hex
    try:
        with TestClient(api.app) as cliente:
            yield SimpleNamespace(
                cliente=cliente,
                gestor=gestor,
                carpeta=carpeta,
                id=id_,
                url=f"/generaciones/{id_}/archivos/dxf",
                token=emitir_token(id_),
            )
    finally:
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(previo)


@pytest.mark.parametrize("formato", ["step", "glb", "csv", "dxf"])
def test_canal_sigue_sirviendo_todos_los_formatos(escenario_dxf, formato):
    """RNF-3/AC3: el canal sirve los formatos previos y el nuevo, con su MIME."""
    respuesta = escenario_dxf.cliente.get(
        f"/generaciones/{escenario_dxf.id}/archivos/{formato}",
        headers={"X-Download-Token": escenario_dxf.token},
    )
    # Arrange/Act arriba; Assert:
    assert respuesta.status_code == 200
    if formato == "dxf":
        assert respuesta.headers["content-type"] == "image/vnd.dxf"
        assert respuesta.headers["content-disposition"] == 'attachment; filename="pieza.dxf"'


def test_ac3_sin_token_devuelve_403(escenario_dxf):
    respuesta = escenario_dxf.cliente.get(escenario_dxf.url)
    assert respuesta.status_code == 403
    assert escenario_dxf.gestor.consultas == 0


def test_ac3_token_ajeno_devuelve_403(escenario_dxf):
    respuesta = escenario_dxf.cliente.get(
        escenario_dxf.url, headers={"X-Download-Token": emitir_token(uuid.uuid4().hex)}
    )
    assert respuesta.status_code == 403
    assert escenario_dxf.gestor.consultas == 0


def test_ac3_token_expirado_devuelve_410(escenario_dxf):
    import time

    token = emitir_token(escenario_dxf.id, ahora=int(time.time()) - 120)
    respuesta = escenario_dxf.cliente.get(escenario_dxf.url, headers={"X-Download-Token": token})
    assert respuesta.status_code == 410


def test_ac3_formtao_desconocido_devuelve_404(escenario_dxf):
    respuesta = escenario_dxf.cliente.get(
        f"/generaciones/{escenario_dxf.id}/archivos/pdf",
        headers={"X-Download-Token": escenario_dxf.token},
    )
    assert respuesta.status_code == 404


def test_ac3_sin_verificacion_devuelve_404(escenario_dxf):
    escenario_dxf.gestor.estado_vuelve("construido")

    respuesta = escenario_dxf.cliente.get(
        escenario_dxf.url, headers={"X-Download-Token": escenario_dxf.token}
    )

    assert respuesta.status_code == 404
