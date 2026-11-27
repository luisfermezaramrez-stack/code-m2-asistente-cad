"""HU-37: historial de solicitudes en la UI (SPEC-038).

Cubre el endpoint de listado (AC3), la persistencia como fuente de verdad
(AC1/AC2), los filtros de RF-2, la protección de S6 y la descarga del STEP de
una solicitud antigua (RF-4/AC4). Sin red, API key ni GPU: el pipeline se
inyecta y el registro es un CSV temporal.
"""

import csv
import json
import secrets

import pytest
from fastapi.testclient import TestClient

from m2_cad import api, seguimiento
from m2_cad.autenticacion import ANONIMO, LimiteIntentos, hash_clave
from m2_cad.registro import CAMPOS, SIN_TRADUCCION, registrar
from m2_cad.trabajos import GestorTrabajos

CLAUBE_ANA = "clave-ana-hu37"
CLAVE_BOB = "clave-bob-hu37"


@pytest.fixture
def registro_temporal(tmp_path, monkeypatch):
    """Aísla el CSV del registro y su directorio de salidas (sin hardware)."""
    ruta = tmp_path / "registro.csv"
    salidas = tmp_path / "outputs"
    salidas.mkdir()
    monkeypatch.setattr(api, "RUTA_DEFAULT", ruta)
    monkeypatch.setattr(api, "obtener_directorio_salidas", lambda: salidas)
    return ruta, salidas


def construir(ruta, identificador, texto, step="pieza.step"):
    """Registra una solicitud construida (resultado con STEP)."""
    return registrar(
        texto=texto,
        traduccion=SIN_TRADUCCION,
        resultado={"step": str(step), "glb": "pieza.glb", "bom_csv": "materiales.csv"},
        latencia_ms=42,
        identificador=identificador,
        ruta=ruta,
    )


def declinar(ruta, identificador, texto):
    """Registra una solicitud declinada con causa del catálogo."""
    return registrar(
        texto=texto,
        traduccion=SIN_TRADUCCION,
        resultado=None,
        latencia_ms=30,
        error=(
            "Pieza declinada: El asistente no puede construir esta pieza: "
            "familia fuera de catálogo."
        ),
        identificador=identificador,
        ruta=ruta,
        causa="familia_no_soportada",
    )


def fallar(ruta, identificador, texto):
    """Registra una solicitud que terminó en error sin causa de declinación."""
    return registrar(
        texto=texto,
        traduccion=SIN_TRADUCCION,
        resultado=None,
        latencia_ms=12,
        error="No fue posible completar la generación.",
        identificador=identificador,
        ruta=ruta,
    )


def test_ac3_el_listado_devuelve_todas_las_solicitudes_sin_ids_conocidos(registro_temporal):
    """AC3: el cliente obtiene el listado de un endpoint, no recorriendo ids."""
    # Arrange
    ruta, _ = registro_temporal
    construir(ruta, "a" * 32, "placa de acero de 100 mm")
    declinar(ruta, "b" * 32, "soporte soldado")
    fallar(ruta, "c" * 32, "brida de 4 pulgadas")

    # Act
    with TestClient(api.app) as cliente:
        respuesta = cliente.get("/v1/registros")

    # Assert
    assert respuesta.status_code == 200
    solicitudes = respuesta.json()["registros"]
    assert {solicitud["id"] for solicitud in solicitudes} == {"a" * 32, "b" * 32, "c" * 32}


def test_ac1_ac2_dos_lecturas_del_mismo_registro_devuelven_lo_mismo(registro_temporal):
    """AC1/AC2: recargar o abrir desde otro equipo devuelve las mismas filas."""
    # Arrange
    ruta, _ = registro_temporal
    construir(ruta, "d" * 32, "espaciador de 14 mm")

    # Act
    with TestClient(api.app) as recarga:
        primera = recarga.get("/v1/registros").json()
    with TestClient(api.app) as otro_equipo:
        segunda = otro_equipo.get("/v1/registros").json()

    # Assert
    assert primera == segunda
    assert [solicitud["texto"] for solicitud in primera["registros"]] == ["espaciador de 14 mm"]


def test_rf2_filtra_por_resultado_y_por_texto(registro_temporal):
    """RF-2: filtros por resultado (construida/declinada) y por descripción."""
    # Arrange
    ruta, _ = registro_temporal
    construir(ruta, "e" * 32, "PLACA de acero de 100 mm")
    declinar(ruta, "f" * 32, "soporte soldado")

    # Act
    with TestClient(api.app) as cliente:
        construidas = cliente.get("/v1/registros", params={"resultado": "construida"}).json()
        declinadas = cliente.get("/v1/registros", params={"resultado": "declinada"}).json()
        por_texto = cliente.get("/v1/registros", params={"texto": "placa"}).json()
        sin_coincidencias = cliente.get("/v1/registros", params={"texto": "tornillo"}).json()

    # Assert
    assert [solicitud["id"] for solicitud in construidas["registros"]] == ["e" * 32]
    assert [solicitud["id"] for solicitud in declinadas["registros"]] == ["f" * 32]
    assert [solicitud["id"] for solicitud in por_texto["registros"]] == ["e" * 32]
    assert sin_coincidencias["registros"] == []


def test_s6_el_listado_solo_expone_los_campos_necesarios(registro_temporal):
    """S6: ni prompt, ni usuario, ni rutas de artefactos en el listado."""
    # Arrange
    ruta, _ = registro_temporal
    construir(ruta, "1" * 32, "placa con api_key=secreto")

    # Act
    with TestClient(api.app) as cliente:
        respuesta = cliente.get("/v1/registros")

    # Assert
    solicitud = respuesta.json()["registros"][0]
    assert set(solicitud) == {"id", "hora", "texto", "estado", "motivo"}
    assert solicitud["estado"] == "construida"
    assert solicitud["motivo"] is None
    assert "prompt" not in respuesta.text
    assert "pieza.glb" not in respuesta.text


def test_rf2_el_motivo_de_error_no_revela_detalles_internos(registro_temporal):
    """RF-2/S6: el motivo de un fallo es un texto público, no la excepción."""
    # Arrange
    ruta, _ = registro_temporal
    fallar(ruta, "2" * 32, "brida de 4 pulgadas")

    # Act
    with TestClient(api.app) as cliente:
        solicitud = cliente.get("/v1/registros").json()["registros"][0]

    # Assert
    assert solicitud["estado"] == "error"
    assert solicitud["motivo"] == "No se pudo completar la solicitud."
    assert "No fue posible" not in json.dumps(solicitud, ensure_ascii=False)


def test_s6_el_listado_exige_sesion_y_solo_muestra_filas_propias(tmp_path, monkeypatch):
    """S6: 401 sin sesión y aislamiento entre usuarios (protección de /v1)."""
    # Arrange
    ruta = tmp_path / "registro.csv"
    monkeypatch.setattr(api, "RUTA_DEFAULT", ruta)
    monkeypatch.setenv("M2_AUTH_ENABLED", "1")
    monkeypatch.setenv("M2_AUTH_SECRET", secrets.token_hex(32))
    hashes = {usuario: hash_clave(clave) for usuario, clave in
              {"ana": CLAUBE_ANA, "bob": CLAVE_BOB}.items()}
    monkeypatch.setenv("M2_AUTH_USERS", json.dumps(hashes))
    monkeypatch.setenv("M2_AUTH_COOKIE_SECURE", "0")
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", secrets.token_hex(32))
    previo = dict(api.app.dependency_overrides)
    api.app.dependency_overrides[api.obtener_gestor_trabajos] = lambda: GestorTrabajos()
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: (
        seguimiento.Configuracion(activo=False)
    )
    api.app.dependency_overrides[api.obtener_limite_login] = lambda: LimiteIntentos()
    try:
        registrar(texto="placa de ana", traduccion=SIN_TRADUCCION, resultado={"step": "a.step"},
                  latencia_ms=1, identificador="3" * 32, ruta=ruta, usuario="ana")
        registrar(texto="placa de bob", traduccion=SIN_TRADUCCION, resultado={"step": "b.step"},
                  latencia_ms=1, identificador="4" * 32, ruta=ruta, usuario="bob")

        # Act
        with TestClient(api.app) as anonimo:
            sin_sesion = anonimo.get("/v1/registros")
        with TestClient(api.app) as cliente:
            cliente.post("/v1/auth/login", json={"usuario": "ana", "clave": CLAUBE_ANA})
            de_ana = cliente.get("/v1/registros").json()["registros"]
        with TestClient(api.app) as cliente:
            cliente.post("/v1/auth/login", json={"usuario": "bob", "clave": CLAVE_BOB})
            de_bob = cliente.get("/v1/registros").json()["registros"]
    finally:
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(previo)

    # Assert
    assert sin_sesion.status_code == 401
    assert [solicitud["texto"] for solicitud in de_ana] == ["placa de ana"]
    assert [solicitud["texto"] for solicitud in de_bob] == ["placa de bob"]


def test_s5_el_listado_ordena_del_mas_reciente_y_recorta_a_doscientas(registro_temporal):
    """S5/S6: orden descendente por hora y recorte de las 200 más recientes."""
    # Arrange
    ruta, _ = registro_temporal
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS)
        escritor.writeheader()
        for indice in range(201):
            escritor.writerow({
                "id": f"{indice:032d}", "hora": f"2026-11-27T00:00:{indice // 60:02d}.{indice:06d}",
                "texto": f"pieza {indice}", "traduccion": SIN_TRADUCCION,
                "resultado": "{'step': 'pieza.step'}", "latencia_ms": "1", "error": "ninguno",
                "version": "desconocida", "usuario": ANONIMO, "causa": "ninguna",
                "prompt": "no aplica", "prompt_hash": "no aplica",
            })

    # Act
    with TestClient(api.app) as cliente:
        solicitudes = cliente.get("/v1/registros").json()["registros"]

    # Assert
    assert len(solicitudes) == 200
    assert [solicitud["hora"] for solicitud in solicitudes] == sorted(
        (solicitud["hora"] for solicitud in solicitudes), reverse=True
    )
    assert solicitudes[0]["texto"] == "pieza 200"


def test_rf4_el_step_se_descarga_tras_reiniciar_con_el_token(registro_temporal, monkeypatch):
    """RF-4/AC4: el token de `GET /registros/{id}` habilita el STEP tras reiniciar."""
    # Arrange
    ruta, salidas = registro_temporal
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", secrets.token_hex(32))
    step = salidas / "pieza.step"
    step.write_text("STEP SIMULADO", encoding="utf-8")
    construir(ruta, "5" * 32, "placa de acero", step=step)
    # Reinicio: ningún trabajo vivo en el gestor de trabajos.
    api.app.dependency_overrides[api.obtener_gestor_trabajos] = lambda: GestorTrabajos()
    try:
        # Act
        with TestClient(api.app) as cliente:
            registro = cliente.get(f"/v1/registros/{'5' * 32}")
            token = registro.headers.get("X-Download-Token")
            con_token = cliente.get(f"/v1/registros/{'5' * 32}/step",
                                    headers={"X-Download-Token": token or ""})
            sin_token = cliente.get(f"/v1/registros/{'5' * 32}/step")
    finally:
        api.app.dependency_overrides.clear()

    # Assert
    assert registro.status_code == 200
    assert token
    assert con_token.status_code == 200
    assert con_token.text == "STEP SIMULADO"
    assert sin_token.status_code == 403


def test_s8_la_consulta_puntual_expone_el_estado_ya_derivado(registro_temporal):
    """S8/RNF-1: `GET /registros/{id}` trae `estado` y `motivo` del backend.

    El cliente no debe repetir la precedencia del estado: la consulta puntual
    expone la misma clasificación que el listado, con `motivo` como cadena
    vacía cuando no hay motivo (el cuerpo es un mapa de texto).
    """
    # Arrange
    ruta, _ = registro_temporal
    construir(ruta, "6" * 32, "placa de acero de 100 mm")
    declinar(ruta, "7" * 32, "soporte soldado")

    # Act
    with TestClient(api.app) as cliente:
        construida = cliente.get(f"/v1/registros/{'6' * 32}").json()
        declinada = cliente.get(f"/v1/registros/{'7' * 32}").json()
        listado = {
            solicitud["id"]: solicitud["estado"]
            for solicitud in cliente.get("/v1/registros").json()["registros"]
        }

    # Assert: el estado y el motivo los deriva el backend, no el cliente.
    assert construida["estado"] == "construida"
    assert construida["motivo"] == ""
    assert declinada["estado"] == "declinada"
    assert declinada["motivo"] == (
        "Pieza declinada: El asistente no puede construir esta pieza: "
        "familia fuera de catálogo."
    )
    # La consulta puntual y el listado coinciden en la clasificación.
    assert construida["estado"] == listado["6" * 32]
    assert declinada["estado"] == listado["7" * 32]
    # Ninguna otra clave de la fila desaparece por añadir las dos nuevas.
    assert construida["id"] == "6" * 32
    assert construida["texto"] == "placa de acero de 100 mm"
