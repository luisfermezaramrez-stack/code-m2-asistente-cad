"""HU-36: pruebas HTTP/CORS sobre la API real, sin motor CAD ni proveedor LLM."""

import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from m2_cad import api
from m2_cad.autenticacion import ANONIMO
from m2_cad.seguridad_descargas import emitir_token, exigir_token


class GestorSimulado:
    def __init__(self, ruta: Path):
        self.ruta = ruta
        self.consultas = 0

    def obtener(self, solicitud_id: str):
        self.consultas += 1
        # Como un Trabajo real, el doble conoce a su dueño (HU-53).
        return SimpleNamespace(
            usuario=ANONIMO,
            estado=lambda: {"estado": "verificado", "resultado": {"step": str(self.ruta)}},
        )


@pytest.fixture
def escenario(tmp_path, monkeypatch):
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", "s" * 64)
    monkeypatch.setenv("M2_DOWNLOAD_TTL_SECONDS", "60")
    carpeta = tmp_path / "outputs"
    carpeta.mkdir()
    archivo = carpeta / "pieza.step"
    archivo.write_text("STEP_SIMULADO", encoding="utf-8")
    gestor = GestorSimulado(archivo)
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
                url=f"/generaciones/{id_}/archivos/step",
                token=emitir_token(id_),
            )
    finally:
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(previo)


@pytest.mark.parametrize("metodo", ["GET", "HEAD"])
def test_descarga_autorizada(escenario, metodo):
    respuesta = escenario.cliente.request(
        metodo, escenario.url, headers={"X-Download-Token": escenario.token}
    )
    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["x-content-type-options"] == "nosniff"
    if metodo == "GET":
        assert respuesta.content == b"STEP_SIMULADO"
    else:
        assert not respuesta.content


@pytest.mark.parametrize("metodo", ["GET", "HEAD"])
def test_descarga_sin_token_devuelve_403(escenario, metodo):
    respuesta = escenario.cliente.request(metodo, escenario.url)
    assert respuesta.status_code == 403
    assert escenario.gestor.consultas == 0


def test_token_de_otra_solicitud_devuelve_403(escenario):
    token_ajeno = emitir_token(uuid.uuid4().hex)
    respuesta = escenario.cliente.get(escenario.url, headers={"X-Download-Token": token_ajeno})
    assert respuesta.status_code == 403
    assert escenario.gestor.consultas == 0


def test_token_expirado_devuelve_410(escenario):
    token = emitir_token(escenario.id, ahora=int(time.time()) - 120)
    respuesta = escenario.cliente.get(escenario.url, headers={"X-Download-Token": token})
    assert respuesta.status_code == 410
    assert escenario.gestor.consultas == 0


def test_uuid_invalido_no_consulta_gestor(escenario):
    respuesta = escenario.cliente.get("/generaciones/no-es-uuid/archivos/step")
    assert respuesta.status_code == 422
    assert escenario.gestor.consultas == 0


def test_archivo_fuera_de_outputs_bloqueado(escenario, tmp_path):
    externo = tmp_path / "otro.step"
    externo.write_text("NO_DEBE_DESCARGARSE", encoding="utf-8")
    escenario.gestor.ruta = externo
    respuesta = escenario.cliente.get(escenario.url, headers={"X-Download-Token": escenario.token})
    assert respuesta.status_code == 404


def test_registro_uuid_invalido_devuelve_422_sin_leer_csv(escenario, monkeypatch):
    def nunca_leer():
        raise AssertionError("No debe consultar CSV con UUID inválido")

    monkeypatch.setattr(api, "obtener_ruta_registro", nunca_leer)
    respuesta = escenario.cliente.get("/registros/no-es-uuid")
    assert respuesta.status_code == 422


@pytest.mark.parametrize("token,esperado", [(None, 403), ("basura", 403)])
def test_descarga_step_registro_exige_token(escenario, token, esperado):
    headers = {"X-Download-Token": token} if token is not None else {}
    respuesta = escenario.cliente.get(f"/registros/{escenario.id}/step", headers=headers)
    assert respuesta.status_code == esperado


def test_descarga_step_registro_expirado(escenario):
    token = emitir_token(escenario.id, ahora=int(time.time()) - 120)
    respuesta = escenario.cliente.get(
        f"/registros/{escenario.id}/step",
        headers={"X-Download-Token": token},
    )
    assert respuesta.status_code == 410


def test_cors_admite_token_y_expone_cabecera(escenario):
    origen = "http://localhost:8000"
    respuesta = escenario.cliente.options(
        escenario.url,
        headers={
            "Origin": origen,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Download-Token",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == origen
    assert "x-download-token" in respuesta.headers["access-control-allow-headers"].lower()
    salud = escenario.cliente.get("/health", headers={"Origin": origen})
    assert salud.status_code == 200
    assert "x-download-token" in salud.headers["access-control-expose-headers"].lower()


def test_json_entrega_token_sin_pipeline(escenario, monkeypatch):
    monkeypatch.setattr(api, "registrar", lambda **kwargs: None)
    monkeypatch.setattr(api, "medir_solicitud", lambda *args, **kwargs: None)
    monkeypatch.setattr(api.seguimiento, "iniciar_corrida", lambda *args, **kwargs: None)
    monkeypatch.setattr(api.seguimiento, "version_modelo", lambda: "simulado")
    api.app.dependency_overrides[api.obtener_procesador] = lambda: (
        lambda texto, medicion: {"resultado": "declinacion", "motivo": "Simulación"}
    )
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: SimpleNamespace(
        experimento_generacion="simulacion"
    )
    respuesta = escenario.cliente.post(
        "/generar",
        headers={"Accept": "application/json"},
        json={"texto": "Placa de simulación"},
    )
    assert respuesta.status_code == 200
    token = respuesta.headers.get("X-Download-Token")
    id_ = respuesta.headers.get("X-Registro-ID")
    assert token and id_
    exigir_token(id_, token)
    assert token not in str(respuesta.json())


class TrabajoSSESimulado:
    def __init__(self):
        self.id = uuid.uuid4().hex

    async def eventos(self, request):
        yield f'event: verificado\ndata: {{"solicitud_id": "{self.id}"}}\n\n'

    def cancelar(self):
        return {"estado": "cancelado"}


class GestorSSESimulado:
    def crear(self, texto, procesador, al_finalizar, usuario=None):
        return TrabajoSSESimulado()


def test_sse_entrega_token_en_cabecera_no_en_eventos(escenario):
    api.app.dependency_overrides[api.obtener_gestor_trabajos] = lambda: GestorSSESimulado()
    api.app.dependency_overrides[api.obtener_procesador_sse] = lambda: (
        lambda texto, control, medicion: {}
    )
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: SimpleNamespace(
        experimento_generacion="simulacion"
    )
    respuesta = escenario.cliente.post(
        "/generar",
        headers={"Accept": "text/event-stream"},
        json={"texto": "Placa de simulación"},
    )
    assert respuesta.status_code == 200
    token = respuesta.headers.get("X-Download-Token")
    id_ = respuesta.headers.get("X-Solicitud-ID")
    assert token and id_
    exigir_token(id_, token)
    assert token not in respuesta.text
