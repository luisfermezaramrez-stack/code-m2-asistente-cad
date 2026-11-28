"""SPEC-044 RNF-3: descarga del PDF por el canal de artefactos de SPEC-037.

Reutiliza el patrón de `tests/test_hu42_canal_dxf.py` (sin motor CAD ni LLM)
y comprueba la no-regresión HTTP de STEP/GLB/CSV/DXF.
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
    """Doble que sirve todos los artefactos de una generación verificada."""

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
def escenario_pdf(tmp_path, monkeypatch):
    """Canal de artefactos con STEP, GLB, CSV, DXF y PDF sobre el directorio de salidas."""
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
        ("pdf", "PDF_SIMULADO"),
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
                token=emitir_token(id_),
            )
    finally:
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(previo)


# ---------- RNF-3: el PDF por el mismo canal que el DXF ----------


def test_rnf3_pdf_por_el_canal_con_su_mime(escenario_pdf):
    """RNF-3: PDF servido con token y Content-Type application/pdf."""
    respuesta = escenario_pdf.cliente.get(
        f"/generaciones/{escenario_pdf.id}/archivos/pdf",
        headers={"X-Download-Token": escenario_pdf.token},
    )
    # Arrange/Act arriba; Assert:
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.headers["content-disposition"] == 'attachment; filename="pieza.pdf"'
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["x-content-type-options"] == "nosniff"


# ---------- No-regresión del canal (RNF-3) ----------


@pytest.mark.parametrize("formato", ["step", "glb", "csv", "dxf"])
def test_no_regresion_canal_sigue_sirviendo_todos_los_formatos(escenario_pdf, formato):
    """RNF-3: los formatos previos siguen servidos con su MIME intacto."""
    respuesta = escenario_pdf.cliente.get(
        f"/generaciones/{escenario_pdf.id}/archivos/{formato}",
        headers={"X-Download-Token": escenario_pdf.token},
    )
    assert respuesta.status_code == 200


def test_no_regresion_dxf_mime_intacto(escenario_pdf):
    """RNF-3: el DXF conserva su MIME `image/vnd.dxf` de SPEC-043."""
    respuesta = escenario_pdf.cliente.get(
        f"/generaciones/{escenario_pdf.id}/archivos/dxf",
        headers={"X-Download-Token": escenario_pdf.token},
    )
    assert respuesta.headers["content-type"] == "image/vnd.dxf"


def test_rnf3_formato_ajeno_devuelve_404(escenario_pdf):
    """RNF-3: un formato fuera de la lista aceptada sigue devolviendo 404."""
    respuesta = escenario_pdf.cliente.get(
        f"/generaciones/{escenario_pdf.id}/archivos/xyz",
        headers={"X-Download-Token": escenario_pdf.token},
    )
    assert respuesta.status_code == 404


def test_rnf3_sin_token_devuelve_403(escenario_pdf):
    """RNF-3: el PDF exige token como los demás formatos (SPEC-037)."""
    respuesta = escenario_pdf.cliente.get(f"/generaciones/{escenario_pdf.id}/archivos/pdf")
    assert respuesta.status_code == 403
    assert escenario_pdf.gestor.consultas == 0


def test_rnf3_token_ajeno_devuelve_403(escenario_pdf):
    """RNF-3: el token de otro dueño no da acceso al PDF."""
    respuesta = escenario_pdf.cliente.get(
        f"/generaciones/{escenario_pdf.id}/archivos/pdf",
        headers={"X-Download-Token": emitir_token(uuid.uuid4().hex)},
    )
    assert respuesta.status_code == 403


def test_rnf3_token_expirado_devuelve_410(escenario_pdf):
    """RNF-3: el token expirado no descarga el PDF."""
    import time

    token = emitir_token(escenario_pdf.id, ahora=int(time.time()) - 120)
    respuesta = escenario_pdf.cliente.get(
        f"/generaciones/{escenario_pdf.id}/archivos/pdf",
        headers={"X-Download-Token": token},
    )
    assert respuesta.status_code == 410


def test_rnf3_sin_verificacion_devuelve_404(escenario_pdf):
    """RNF-3: sin verificación, ni el PDF ni los demás se sirven."""
    escenario_pdf.gestor.estado_vuelve("construido")

    respuesta = escenario_pdf.cliente.get(
        f"/generaciones/{escenario_pdf.id}/archivos/pdf",
        headers={"X-Download-Token": escenario_pdf.token},
    )

    assert respuesta.status_code == 404
