"""HU-53: acceso anónimo, aislamiento entre usuarios y trazabilidad (SPEC-054)."""

import csv
import json
import secrets
import sys
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from m2_cad import api, seguimiento
from m2_cad.autenticacion import (
    COOKIE_NOMBRE,
    emitir_sesion,
    hash_clave,
    usuarios,
    validar_sesion,
    verificar_clave,
    verificar_usuario,
)
from m2_cad.registro import CAMPOS, registrar
from m2_cad.trabajos import GestorTrabajos


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Autenticación activa, dos usuarios y dependencias aisladas del hardware."""
    gestor = GestorTrabajos()
    claves = {"ana": "clave-ana-53", "bob": "clave-bob-53"}
    hashes = {usuario: hash_clave(clave) for usuario, clave in claves.items()}
    monkeypatch.setenv("M2_AUTH_ENABLED", "1")
    monkeypatch.setenv("M2_AUTH_SECRET", secrets.token_hex(32))
    monkeypatch.setenv("M2_AUTH_USERS", json.dumps(hashes))
    monkeypatch.setenv("M2_AUTH_COOKIE_SECURE", "0")
    monkeypatch.setenv("M2_AUTH_TTL_SECONDS", "3600")
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", secrets.token_hex(32))
    ruta_registro = tmp_path / "registro.csv"
    monkeypatch.setattr(api, "RUTA_DEFAULT", ruta_registro)
    previo = dict(api.app.dependency_overrides)
    api.app.dependency_overrides[api.obtener_gestor_trabajos] = lambda: gestor
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: (
        seguimiento.Configuracion(activo=False)
    )
    try:
        yield SimpleNamespace(
            gestor=gestor,
            claves=claves,
            ruta_registro=ruta_registro,
            tmp_path=tmp_path,
        )
    finally:
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(previo)


def entrar(usuario: str, clave: str) -> TestClient:
    cliente = TestClient(api.app)
    respuesta = cliente.post("/auth/login", json={"usuario": usuario, "clave": clave})
    assert respuesta.status_code == 200
    return cliente


def generar_sse(cliente: TestClient, archivo) -> tuple[str, str]:
    def procesar(texto, control, medicion=None):
        control.informar("validando")
        control.informar("generando")
        return {"step": str(archivo)}

    api.app.dependency_overrides[api.obtener_procesador_sse] = lambda: procesar
    respuesta = cliente.post(
        "/generar",
        json={"texto": "Espaciador de 14 mm"},
        headers={"Accept": "text/event-stream"},
    )
    assert respuesta.status_code == 200
    return respuesta.headers["x-registro-id"], respuesta.headers["x-download-token"]


def filas_csv(ruta) -> list[dict[str, str]]:
    with ruta.open(newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def test_ac1_ac4_anónimo_no_genera_y_salud_queda_abierta(entorno):
    with TestClient(api.app) as cliente:
        assert cliente.get("/health").status_code == 200
        assert cliente.get("/ready").status_code != 401  # salud abierta, sin sesión
        assert cliente.get("/auth/me").json() == {
            "requerido": True,
            "autenticado": False,
            "usuario": None,
        }
        identificador = uuid.uuid4().hex
        assert cliente.post("/generar", json={"texto": "Placa"}).status_code == 401
        assert cliente.get(f"/generaciones/{identificador}").status_code == 401
        assert cliente.delete(f"/generaciones/{identificador}").status_code == 401
        assert cliente.get(f"/registros/{identificador}").status_code == 401

    assert not entorno.ruta_registro.exists()
    assert not entorno.gestor._trabajos


def test_ac2_aislamiento_de_trabajos_registro_y_descargas(entorno):
    salidas = entorno.tmp_path / "outputs"
    salidas.mkdir()
    archivo = salidas / "pieza.step"
    archivo.write_text("STEP_DE_ANA", encoding="utf-8")
    api.app.dependency_overrides[api.obtener_directorio_salidas] = lambda: salidas
    with entrar("ana", entorno.claves["ana"]) as ana:
        identificador, token = generar_sse(ana, archivo)
        with entrar("bob", entorno.claves["bob"]) as bob:
            assert ana.get(f"/generaciones/{identificador}").status_code == 200
            assert bob.get(f"/generaciones/{identificador}").status_code == 404
            assert bob.delete(f"/generaciones/{identificador}").status_code == 404
            assert bob.get(f"/registros/{identificador}").status_code == 404
            assert (
                bob.get(
                    f"/generaciones/{identificador}/archivos/step",
                    headers={"X-Download-Token": token},
                ).status_code
                == 404
            )
            assert (
                bob.get(
                    f"/registros/{identificador}/step", headers={"X-Download-Token": token}
                ).status_code
                == 404
            )
            descarga = ana.get(
                f"/generaciones/{identificador}/archivos/step",
                headers={"X-Download-Token": token},
            )
            assert descarga.status_code == 200
            assert descarga.content == b"STEP_DE_ANA"
            assert ana.get(f"/registros/{identificador}").json()["usuario"] == "ana"

    fila = filas_csv(entorno.ruta_registro)
    assert len(fila) == 1
    assert fila[0]["id"] == identificador
    assert fila[0]["usuario"] == "ana"
    assert "clave-ana-53" not in json.dumps(fila, ensure_ascii=False)


def test_login_invalido_cookie_firmada_y_logout(entorno):
    with TestClient(api.app) as cliente:
        assert (
            cliente.post("/auth/login", json={"usuario": "ana", "clave": "incorrecta"}).status_code
            == 401
        )
        assert (
            cliente.post("/auth/login", json={"usuario": "nadie", "clave": "x"}).status_code == 401
        )
        respuesta = cliente.post(
            "/auth/login", json={"usuario": "ana", "clave": entorno.claves["ana"]}
        )
        assert respuesta.status_code == 200
        assert respuesta.json() == {"autenticado": True, "usuario": "ana"}
        cookie = respuesta.headers["set-cookie"]
        assert COOKIE_NOMBRE in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie
        assert "Secure" not in cookie
        assert cliente.get("/auth/me").json()["usuario"] == "ana"
        assert cliente.post("/auth/logout").json() == {"autenticado": False}
        assert cliente.get("/auth/me").json()["autenticado"] is False


def test_cookie_manipulada_o_expirada_no_autentica(entorno):
    token = emitir_sesion("ana", ahora=1_000)
    assert validar_sesion(token, ahora=1_500) == "ana"
    assert validar_sesion(token, ahora=1_000 + 3_600) is None
    firma = token.rsplit(".", 1)[1]
    manipulada = token.rsplit(".", 1)[0] + "." + ("0" if firma[0] != "0" else "1") + firma[1:]
    assert validar_sesion(manipulada, ahora=1_500) is None
    assert validar_sesion("v1.basura.2000000000." + "0" * 64, ahora=1_500) is None

    with TestClient(api.app) as cliente:
        cliente.cookies.set(COOKIE_NOMBRE, manipulada)
        assert cliente.get("/auth/me").json()["autenticado"] is False
        assert cliente.post("/generar", json={"texto": "Placa"}).status_code == 401


def test_hash_pbkdf2_y_cli(monkeypatch, capsys):
    guardado = hash_clave("clave-secreta")
    assert guardado.startswith("pbkdf2_sha256$")
    assert verificar_clave("clave-secreta", guardado)
    assert not verificar_clave("otra", guardado)
    assert not verificar_clave("clave-secreta", "basura")

    from m2_cad.usuarios import main

    monkeypatch.setenv("M2_CLAVE_NUEVA", "clave-cli")
    monkeypatch.setattr(sys, "argv", ["usuarios", "hash"])
    assert main() == 0
    hash_cli = capsys.readouterr().out.strip()
    assert verificar_clave("clave-cli", hash_cli)


def test_modo_local_explícito_sigue_anónimo(entorno, monkeypatch):
    monkeypatch.setenv("M2_AUTH_ENABLED", "0")

    def procesar(texto, medicion=None):
        return {"resultado": "pieza"}

    api.app.dependency_overrides[api.obtener_procesador] = lambda: procesar
    with TestClient(api.app) as cliente:
        assert cliente.get("/auth/me").json()["requerido"] is False
        respuesta = cliente.post("/generar", json={"texto": "Placa"})
        assert respuesta.status_code == 200
        assert cliente.get(respuesta.headers["x-registro-url"]).json()["usuario"] == "anónimo"
    api.app.dependency_overrides.pop(api.obtener_procesador, None)


@pytest.mark.parametrize(
    ("valor", "patron"),
    [("abc", "entero"), ("1", "entre"), ("9999999", "entre")],
)
def test_configuracion_ttl_invalida(monkeypatch, valor, patron):
    monkeypatch.setenv("M2_AUTH_SECRET", secrets.token_hex(32))
    monkeypatch.setenv("M2_AUTH_TTL_SECONDS", valor)
    with pytest.raises(RuntimeError, match=patron):
        emitir_sesion("ana", ahora=1)


def test_configuracion_usuarios_invalida(monkeypatch):
    monkeypatch.setenv("M2_AUTH_SECRET", secrets.token_hex(32))
    for valor, patron in [
        ("", "M2_AUTH_USERS"),
        ("{", "JSON"),
        ("{}", "al menos"),
        ('{"ana!": "x"}', "inválido"),
    ]:
        monkeypatch.setenv("M2_AUTH_USERS", valor)
        with pytest.raises(RuntimeError, match=patron):
            usuarios()


def test_usuario_invalido_y_login_desactivado(entorno, monkeypatch):
    assert verificar_usuario("ana!", entorno.claves["ana"]) is False
    monkeypatch.setenv("M2_AUTH_ENABLED", "0")
    with TestClient(api.app) as cliente:
        assert (
            cliente.post(
                "/auth/login", json={"usuario": "ana", "clave": entorno.claves["ana"]}
            ).status_code
            == 404
        )


def test_csv_anterior_se_migra_sin_perder_filas(tmp_path):
    ruta = tmp_path / "registro.csv"
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS[:-1])
        escritor.writeheader()
        escritor.writerow({campo: "valor" for campo in CAMPOS[:-1]} | {"id": "anterior"})

    registrar(
        texto="Placa",
        traduccion="no aplica",
        resultado={},
        latencia_ms=1,
        ruta=ruta,
        identificador="nuevo",
        usuario="ana",
    )
    filas = filas_csv(ruta)
    assert [fila["id"] for fila in filas] == ["anterior", "nuevo"]
    assert filas[0]["usuario"] == "anónimo"
    assert filas[1]["usuario"] == "ana"
