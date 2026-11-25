"""HU-36: pruebas unitarias sin red, GPU ni claves de API."""

import uuid

import pytest
from fastapi import HTTPException

from m2_cad.seguridad_descargas import emitir_token, exigir_token, validar_uuid


@pytest.fixture(autouse=True)
def configuracion_segura(monkeypatch):
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", "a" * 64)
    monkeypatch.setenv("M2_DOWNLOAD_TTL_SECONDS", "60")


def comprobar_error(codigo, accion):
    with pytest.raises(HTTPException) as exc:
        accion()
    assert exc.value.status_code == codigo


def test_uuid_valido_en_formato_hex_y_con_guiones():
    identificador = uuid.uuid4()
    assert validar_uuid(identificador.hex) == identificador.hex
    assert validar_uuid(str(identificador).upper()) == identificador.hex


@pytest.mark.parametrize(
    "identificador", ["", "cualquiera", "../archivo", "x" * 32, "0" * 31, "0" * 33]
)
def test_uuid_invalido_devuelve_422(identificador):
    comprobar_error(422, lambda: validar_uuid(identificador))


def test_token_de_solicitud_valido():
    identificador = uuid.uuid4().hex
    token = emitir_token(identificador, ahora=1000)
    assert token.startswith("v1." + identificador + ".1060.")
    assert exigir_token(identificador, token, ahora=1059) is None


def test_sin_token_devuelve_403():
    identificador = uuid.uuid4().hex
    comprobar_error(403, lambda: exigir_token(identificador, None, ahora=1000))


def test_token_de_otra_solicitud_devuelve_403():
    primero, segundo = uuid.uuid4().hex, uuid.uuid4().hex
    token = emitir_token(primero, ahora=1000)
    comprobar_error(403, lambda: exigir_token(segundo, token, ahora=1000))


def test_token_manipulado_devuelve_403():
    identificador = uuid.uuid4().hex
    token = emitir_token(identificador, ahora=1000)
    token_alterado = token[:-1] + ("0" if token[-1] != "0" else "1")
    comprobar_error(403, lambda: exigir_token(identificador, token_alterado, ahora=1000))


def test_token_malformado_devuelve_403():
    identificador = uuid.uuid4().hex
    comprobar_error(403, lambda: exigir_token(identificador, "falso", ahora=1000))


def test_expiracion_exacta_devuelve_410():
    identificador = uuid.uuid4().hex
    token = emitir_token(identificador, ahora=1000)
    comprobar_error(410, lambda: exigir_token(identificador, token, ahora=1060))
    comprobar_error(410, lambda: exigir_token(identificador, token, ahora=1061))


def test_uuid_invalido_se_rechaza_antes_de_verificar_token():
    comprobar_error(422, lambda: exigir_token("../../x", None, ahora=1000))


def test_secreto_inexistente_rechaza_emision(monkeypatch):
    monkeypatch.delenv("M2_DOWNLOAD_SECRET")
    with pytest.raises(RuntimeError, match="M2_DOWNLOAD_SECRET"):
        emitir_token(uuid.uuid4().hex, ahora=1000)


@pytest.mark.parametrize("ttl", ["abc", "0", "2592001", "-1"])
def test_ttl_invalido_rechaza_emision(monkeypatch, ttl):
    monkeypatch.setenv("M2_DOWNLOAD_TTL_SECONDS", ttl)
    with pytest.raises(RuntimeError, match="M2_DOWNLOAD_TTL_SECONDS|expiración"):
        emitir_token(uuid.uuid4().hex, ahora=1000)
