"""Pruebas de la API FastAPI (HU-06).

Cubre POST /generar (200 con STEP o declinación; 422 ante texto vacío o de más
de 1000 caracteres), GET /health en ≤ 1 s y el registro sin campos vacíos ni
datos personales. Cobertura objetivo ≥ 80 % del módulo.
"""

import pytest


def test_modulo_api_importable():
    from m2_cad import api

    assert api is not None


def test_health_endpoint():
    """Verifica que la API responda correctamente."""
    from fastapi.testclient import TestClient

    from m2_cad.api import app

    client = TestClient(app)
    respuesta = client.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "texto",
    [
        "",
        "   ",
        "x" * 1001,
    ],
)
def test_generar_rechaza_entrada_invalida(texto):
    """Verifica que la API rechace solicitudes inválidas."""
    from fastapi.testclient import TestClient

    from m2_cad.api import app

    client = TestClient(app)
    respuesta = client.post("/generar", json={"texto": texto})

    assert respuesta.status_code == 422


def test_generar_con_procesador_simulado():
    """Verifica la respuesta HTTP 200 sin ejecutar el pipeline CAD."""
    from fastapi.testclient import TestClient

    from m2_cad.api import app, obtener_procesador

    # Simula una declinación válida del pipeline CAD.
    def procesador_simulado(texto: str) -> dict[str, str]:
        assert texto == "Placa de 120 mm"
        return {
            "resultado": "declinacion",
            "motivo": "Pieza fuera del catálogo",
        }

    # Sustituye temporalmente el procesador real.
    app.dependency_overrides[obtener_procesador] = lambda: procesador_simulado

    try:
        with TestClient(app) as client:
            respuesta = client.post(
                "/generar",
                json={"texto": "Placa de 120 mm"},
            )

        assert respuesta.status_code == 200
        assert respuesta.json() == {
            "resultado": "declinacion",
            "motivo": "Pieza fuera del catálogo",
        }
    finally:
        # Restaura las dependencias para no afectar otras pruebas.
        app.dependency_overrides.pop(obtener_procesador, None)


def test_generar_pipeline_no_disponible():
    """Verifica que la API informe si el pipeline no está disponible."""
    from fastapi.testclient import TestClient

    from m2_cad.api import app

    with TestClient(app) as client:
        respuesta = client.post(
            "/generar",
            json={"texto": "Placa de 120 mm"},
        )

    assert respuesta.status_code == 503
    assert respuesta.json() == {"detail": "El pipeline CAD aún no está disponible."}


def test_generar_archivos_cad_simulados():
    """Valida la respuesta de generación sin ejecutar el motor CAD."""
    from fastapi.testclient import TestClient

    from m2_cad.api import app, obtener_procesador

    # Simula el resultado esperado del pipeline.
    def procesador_simulado(texto: str) -> dict[str, str]:
        assert texto == "Placa de 120 mm"
        return {
            "resultado": "generada",
            "step": "pieza.step",
            "glb": "pieza.glb",
            "csv": "materiales.csv",
        }

    app.dependency_overrides[obtener_procesador] = lambda: procesador_simulado

    try:
        with TestClient(app) as client:
            respuesta = client.post(
                "/generar",
                json={"texto": "Placa de 120 mm"},
            )

        assert respuesta.status_code == 200
        assert respuesta.json() == {
            "resultado": "generada",
            "step": "pieza.step",
            "glb": "pieza.glb",
            "csv": "materiales.csv",
        }
    finally:
        app.dependency_overrides.pop(obtener_procesador, None)


# --- Registro de solicitudes (HU-06, parte de Luis Meza: AC3 y AC4) ---


def _preparar_registro(monkeypatch, tmp_path):
    """Aísla el CSV de registro en un directorio temporal."""
    from m2_cad import api

    ruta = tmp_path / "registro.csv"
    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: ruta)
    return ruta


def leer_registro_csv(ruta):
    """Lee el CSV de registro como lista de diccionarios."""
    import csv

    with open(ruta, newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def test_generar_20_llamadas_sin_campos_vacios(tmp_path, monkeypatch):
    """En 20 llamadas a POST /generar, 0 campos vacíos en el registro (AC3)."""
    from fastapi.testclient import TestClient

    from m2_cad import api

    ruta = _preparar_registro(monkeypatch, tmp_path)
    api.app.dependency_overrides[api.obtener_procesador] = lambda: (
        lambda texto: {"resultado": "generada"}
    )

    try:
        with TestClient(api.app) as client:
            for i in range(20):
                respuesta = client.post("/generar", json={"texto": f"Placa {i} de 120 mm"})
                assert respuesta.status_code == 200
    finally:
        api.app.dependency_overrides.pop(api.obtener_procesador, None)

    filas = leer_registro_csv(ruta)
    assert len(filas) == 20
    for fila in filas:
        for campo in fila:
            assert fila[campo] != "", f"campo vacío: {campo}"


def test_generar_registra_error_del_pipeline(tmp_path, monkeypatch):
    """Ante fallo del pipeline, error captura el fallo y la fila queda completa."""
    from fastapi.testclient import TestClient

    from m2_cad import api

    ruta = _preparar_registro(monkeypatch, tmp_path)

    with TestClient(api.app) as client:
        respuesta = client.post("/generar", json={"texto": "Placa de 120 mm"})

    assert respuesta.status_code == 503
    filas = leer_registro_csv(ruta)
    assert len(filas) == 1
    fila = filas[0]
    assert "pipeline" in fila["error"]
    for campo in fila:
        assert fila[campo] != "", f"campo vacío: {campo}"


def test_generar_registra_sin_datos_personales(tmp_path, monkeypatch):
    """El registro de la API excluye correos (AC4, Ley 1581)."""
    from fastapi.testclient import TestClient

    from m2_cad import api

    ruta = _preparar_registro(monkeypatch, tmp_path)
    app_dependency = api.obtener_procesador
    api.app.dependency_overrides[app_dependency] = lambda: (
        lambda texto: {"resultado": "generada"}
    )

    try:
        with TestClient(api.app) as client:
            respuesta = client.post(
                "/generar",
                json={"texto": "Placa para ana.lopez@example.com"},
            )
        assert respuesta.status_code == 200
    finally:
        api.app.dependency_overrides.pop(app_dependency, None)

    contenido = ruta.read_text(encoding="utf-8")
    assert "@" not in contenido


def test_generar_conserva_respuesta_con_registro(tmp_path, monkeypatch):
    """El registro no altera la respuesta de POST /generar (comportamiento previo)."""
    from fastapi.testclient import TestClient

    from m2_cad import api

    _preparar_registro(monkeypatch, tmp_path)
    app_dependency = api.obtener_procesador
    api.app.dependency_overrides[app_dependency] = lambda: (
        lambda texto: {"resultado": "generada", "step": "p.step"}
    )

    try:
        with TestClient(api.app) as client:
            respuesta = client.post("/generar", json={"texto": "Placa de 120 mm"})
    finally:
        api.app.dependency_overrides.pop(app_dependency, None)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"resultado": "generada", "step": "p.step"}


def _resultado_pieza(tmp_path):
    """Resultado de pipeline mínimo para probar la integración con la API."""
    from m2_cad.pipeline import ResultadoPieza

    return ResultadoPieza(
        programa={"parts": [], "mates": []},
        step=tmp_path / "pieza.step",
        glb=tmp_path / "pieza.glb",
        bom_csv=tmp_path / "pieza.csv",
        volumen_mm3=1256.64,
        caja_mm=(14.0, 14.0, 10.0),
        tiempo_construccion_s=0.25,
        tiempo_generacion_s=1.5,
        traduccion="a steel spacer",
    )


def test_generar_usa_pipeline_cuando_el_modelo_esta_configurado(tmp_path, monkeypatch):
    """HU-04: con LLM_BASE_URL, /generar entrega STEP, GLB, CSV y tiempos."""
    pytest.importorskip("cadquery")
    from fastapi.testclient import TestClient

    from m2_cad import api, pipeline

    ruta = _preparar_registro(monkeypatch, tmp_path)
    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline, "generar_pieza", lambda texto: _resultado_pieza(tmp_path))

    with TestClient(api.app) as client:
        respuesta = client.post("/generar", json={"texto": "Espaciador de 14 mm"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["step"].endswith("pieza.step")
    assert cuerpo["glb"].endswith("pieza.glb")
    assert cuerpo["bom_csv"].endswith("pieza.csv")
    assert cuerpo["tiempo_generacion_s"] == "1.500"
    assert cuerpo["tiempo_construccion_s"] == "0.250"
    filas = leer_registro_csv(ruta)
    assert "tiempo_construccion_s" in filas[0]["resultado"]


@pytest.mark.parametrize(
    ("error", "codigo"),
    [
        ("declinada", 422),
        ("verificacion", 422),
        ("modelo", 503),
    ],
)
def test_generar_traduce_errores_del_pipeline(tmp_path, monkeypatch, error, codigo):
    """HU-04: los errores del pipeline llegan como HTTP y quedan registrados."""
    pytest.importorskip("cadquery")
    from fastapi.testclient import TestClient

    from m2_cad import api, pipeline

    errores = {
        "declinada": pipeline.PiezaDeclinada("gear train"),
        "verificacion": pipeline.ErrorVerificacion("unknown part type"),
        "modelo": pipeline.ModeloNoDisponible("timeout"),
    }

    def fallar(texto):
        raise errores[error]

    ruta = _preparar_registro(monkeypatch, tmp_path)
    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline, "generar_pieza", fallar)

    with TestClient(api.app) as client:
        respuesta = client.post("/generar", json={"texto": "Engranaje helicoidal"})

    assert respuesta.status_code == codigo
    assert leer_registro_csv(ruta)[0]["error"] != "ninguno"
