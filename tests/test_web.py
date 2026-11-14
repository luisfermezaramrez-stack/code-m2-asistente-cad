"""HU-15: estáticos del mismo origen, errores API JSON y CORS sin comodines."""

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from m2_cad import api
from m2_cad.web import configurar_web, origenes_frontend


@pytest.fixture
def cliente(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<html lang="es">SPA de prueba</html>', encoding="utf-8")
    (dist / "assets" / "index-hash.js").write_text("export const prueba = true", encoding="utf-8")
    app = FastAPI()
    configurar_web(app, directorio=dist, origenes=["https://cad.example.edu"])
    with TestClient(app) as client:
        yield client


def test_estaticos_y_head(cliente):
    response = cliente.get("/")
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-cache"
    assert cliente.head("/").content == b""
    js = cliente.get("/assets/index-hash.js")
    assert js.status_code == 200 and "export const" in js.text
    assert "immutable" in js.headers["cache-control"]
    assert cliente.head("/assets/index-hash.js").content == b""


@pytest.mark.parametrize(
    "ruta",
    [
        "/api/no-existe",
        "/generar/no-existe",
        "/generaciones/no-existe/otra",
        "/health/no-existe",
        "/ruta-desconocida",
        "/assets/ausente.js",
        "/assets/%2e%2e/index.html",
    ],
)
def test_rutas_desconocidas_nunca_caen_en_html(cliente, ruta):
    response = cliente.get(ruta)
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/json"
    assert "<html" not in response.text


def test_build_ausente_no_finge_interfaz_lista(tmp_path):
    app = FastAPI()
    configurar_web(app, directorio=tmp_path)
    with TestClient(app) as client:
        assert client.get("/").status_code == 503
        assert client.get("/").headers["content-type"] == "application/json"


def test_cors_solo_origen_exacto_y_metodos_necesarios(cliente):
    headers = {
        "Origin": "https://cad.example.edu",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, Accept",
    }
    response = cliente.options("/generar", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://cad.example.edu"
    assert "*" not in response.headers["access-control-allow-methods"]
    assert "access-control-allow-credentials" not in response.headers
    response = cliente.get("/", headers={"Origin": "https://cad.example.edu"})
    assert "X-Solicitud-ID" in response.headers["access-control-expose-headers"]
    for origen in ["https://otro.example", "https://cad.example.edu.otro.example"]:
        response = cliente.options("/generar", headers={**headers, "Origin": origen})
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers
    response = cliente.options(
        "/generar", headers={**headers, "Access-Control-Request-Method": "PATCH"}
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "valor",
    [
        "*",
        "https://*.example",
        "https://user:clave@example.edu",
        "file:///tmp",
        "https://cad.example/ruta",
    ],
)
def test_configuracion_cors_rechaza_origenes_no_validos(monkeypatch, valor):
    monkeypatch.setenv("M2_CORS_ORIGINS", valor)
    with pytest.raises(ValueError):
        origenes_frontend()


def test_cors_vacio_solo_mismo_origen_y_lista_explicita(monkeypatch):
    monkeypatch.setenv("M2_CORS_ORIGINS", "")
    assert origenes_frontend() == []
    monkeypatch.setenv("M2_CORS_ORIGINS", "https://cad.example.edu/, http://localhost:5173")
    assert origenes_frontend() == ["https://cad.example.edu", "http://localhost:5173"]


def test_api_real_sirve_build_vue_y_conserva_errores_json():
    """Necesita npm run build, igual que el despliegue y el orden de CI."""
    with TestClient(api.app) as client:
        response = client.get("/")
        assert response.status_code == 200, "Construye primero frontend con npm run build"
        assert '<div id="app">' in response.text
        assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', response.text)
        assert assets
        for url in assets:
            asset = client.get(url)
            assert asset.status_code == 200 and "<html" not in asset.text
        assert client.get("/health").json() == {"status": "ok"}
        assert client.post("/generar", json={"texto": " "}).status_code == 422
        assert client.get("/api/no-existe").status_code == 404
        assert client.get("/api/no-existe").headers["content-type"] == "application/json"
