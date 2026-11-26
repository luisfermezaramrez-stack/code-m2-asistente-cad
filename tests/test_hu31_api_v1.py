"""SPEC-032 / HU-31: API `/v1`, contrato congelado y rutas planas (AC1–AC4).

Sin red, API key ni GPU: el procesador se inyecta y MLflow queda desactivado.
"""

import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from m2_cad import api, contrato_api
from m2_cad.seguimiento import Configuracion

RUTAS_PLANAS = (
    ("/health", "GET"),
    ("/ready", "GET"),
    ("/registros/abc", "GET"),
    ("/registros/abc/step", "GET"),
    ("/generar", "POST"),
    ("/generaciones/abc", "GET"),
    ("/generaciones/abc", "DELETE"),
    ("/generaciones/abc/archivos/step", "GET"),
    ("/generaciones/abc/archivos/step", "HEAD"),
)


@pytest.fixture(autouse=True)
def entorno_simulado(monkeypatch, tmp_path):
    """Aísla registro, salidas, tokens y seguimiento de esta HU."""
    monkeypatch.setenv("LLM_BASE_URL", "http://modelo-simulado")
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", "s" * 64)
    monkeypatch.setattr(api, "RUTA_DEFAULT", tmp_path / "registro.csv")
    salidas = tmp_path / "salidas"
    salidas.mkdir()
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: Configuracion(
        activo=False
    )
    api.app.dependency_overrides[api.obtener_directorio_salidas] = lambda: salidas
    monkeypatch.setattr(api, "obtener_directorio_salidas", lambda: salidas)
    yield salidas
    api.app.dependency_overrides.pop(api.obtener_configuracion_seguimiento, None)
    api.app.dependency_overrides.pop(api.obtener_directorio_salidas, None)


def _procesador_con_step(ruta: Path):
    """Procesador simulado que entrega un STEP real dentro del directorio aislado."""

    def procesar(texto: str, medicion: dict | None = None) -> dict[str, str]:
        return {"resultado": "entregada", "step": str(ruta), "modelo": "simulado"}

    return procesar


@pytest.mark.parametrize("prefijo", ["", "/v1"])
def test_ac1_cliente_plano_y_v1_obtienen_la_misma_respuesta(prefijo, entorno_simulado):
    # Arrange
    paso = entorno_simulado / "pieza.step"
    paso.write_bytes(b"ISO-10303-21;\nSTEP simulado")
    api.app.dependency_overrides[api.obtener_procesador] = lambda: _procesador_con_step(paso)
    try:
        # Act
        with TestClient(api.app) as client:
            respuesta = client.post(f"{prefijo}/generar", json={"texto": "Espaciador de 14 mm"})
            identificador = respuesta.headers["X-Registro-ID"]
            consulta = client.get(f"{prefijo}/registros/{identificador}")
            descarga = client.get(
                respuesta.headers["X-Step-URL"],
                headers={"X-Download-Token": respuesta.headers["X-Download-Token"]},
            )
    finally:
        api.app.dependency_overrides.pop(api.obtener_procesador, None)

    # Assert
    assert respuesta.status_code == 200
    assert consulta.json()["id"] == identificador
    assert descarga.status_code == 200 and descarga.content == paso.read_bytes()
    assert respuesta.headers["X-Registro-URL"].startswith("http://testserver/v1/registros/")
    assert respuesta.headers["X-Step-URL"].startswith("http://testserver/v1/registros/")


@pytest.mark.parametrize(("ruta", "metodo"), RUTAS_PLANAS)
def test_ac1_rutas_planas_redirigen_con_deprecacion(ruta, metodo):
    # Arrange
    peticion = {"json": {"texto": "Placa"}} if metodo == "POST" else {}

    # Act
    with TestClient(api.app) as client:
        respuesta = client.request(metodo, ruta, follow_redirects=False, **peticion)

    # Assert
    assert respuesta.status_code == 307
    assert respuesta.headers["location"].startswith("http://testserver/v1")
    assert respuesta.headers["deprecation"] == api.DEPRECACION_RUTAS_PLANAS
    assert api.DEPRECACION_RUTAS_PLANAS.startswith("@")
    assert respuesta.headers["sunset"] == api.SUNSET_RUTAS_PLANAS
    assert 'rel="successor-version"' in respuesta.headers["link"]


def test_ac1_redireccion_conserva_la_query():
    # Act
    with TestClient(api.app) as client:
        respuesta = client.get("/registros/abc?origen=prueba", follow_redirects=False)

    # Assert
    assert respuesta.headers["location"] == "http://testserver/v1/registros/abc?origen=prueba"


def test_ac1_redireccion_respeta_root_path():
    # Act
    with TestClient(api.app, root_path="/api") as client:
        respuesta = client.get("/health", follow_redirects=False)

    # Assert
    assert respuesta.status_code == 307
    assert respuesta.headers["location"] == "http://testserver/api/v1/health"


def test_ac2_quitar_un_campo_del_esquema_rompe_el_contrato():
    # Arrange
    generado = api.app.openapi()
    modificado = copy.deepcopy(generado)
    propiedades = modificado["components"]["schemas"]["EstadoTrabajo"]["properties"]
    propiedades.pop("estado")

    # Act / Assert
    with pytest.raises(AssertionError, match="EstadoTrabajo.*estado"):
        contrato_api.validar_contrato(modificado, contrato_api.cargar_contrato())


def test_ac3_el_openapi_publicado_solo_contiene_v1_y_esta_congelado():
    # Arrange
    esquema = api.app.openapi()

    # Assert
    assert esquema["info"]["version"] == "1.0.0"
    rutas = esquema["paths"]
    assert rutas and all(ruta.startswith("/v1/") for ruta in rutas)
    contrato_api.validar_contrato(esquema, contrato_api.cargar_contrato())


def test_ac4_la_politica_de_deprecacion_esta_documentada():
    # Arrange
    documento = Path(__file__).resolve().parents[1] / "docs" / "versionado-api.md"

    # Act
    texto = documento.read_text(encoding="utf-8")

    # Assert
    assert "90 días" in texto
    assert "Deprecation" in texto and "Sunset" in texto
    assert "RFC 9745" in texto and "RFC 8594" in texto
    assert api.DEPRECACION_RUTAS_PLANAS in texto
    assert api.SUNSET_RUTAS_PLANAS in texto
    assert "follow_redirects" in texto and "curl -L" in texto


@pytest.mark.parametrize("prefijo", ["", "/v1"])
def test_regresion_entrada_invalida_sigue_registrandose(prefijo):
    # Act
    with TestClient(api.app) as client:
        respuesta = client.post(f"{prefijo}/generar", json={"texto": " "})

    # Assert
    assert respuesta.status_code == 422
    assert respuesta.headers["X-Registro-ID"]
    assert respuesta.headers["X-Registro-URL"].startswith("http://testserver/v1/registros/")
