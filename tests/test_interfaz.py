"""Pruebas de la interfaz Gradio (HU-08), sin llamadas reales a la API."""

from io import BytesIO
from urllib.error import HTTPError

import pytest

from m2_cad import interfaz as ui


@pytest.fixture
def directorio_salidas(tmp_path, monkeypatch):
    """Prepara un directorio outputs temporal para cada prueba."""
    salidas = tmp_path / "outputs"
    salidas.mkdir()

    monkeypatch.setattr(ui, "RAIZ", tmp_path)
    monkeypatch.setattr(ui, "SALIDAS", salidas)

    return salidas


@pytest.mark.parametrize("texto", ["", "   ", "a" * 1001])
def test_rechaza_entrada_invalida(texto, monkeypatch):
    """No envía solicitudes vacías o demasiado largas."""

    def api_no_debe_llamarse(_texto):
        raise AssertionError("No se debe consultar FastAPI")

    monkeypatch.setattr(ui, "consultar_api", api_no_debe_llamarse)

    estado, modelo, step, csv = ui.procesar_solicitud(texto)

    assert "entre 1 y 1000 caracteres" in estado
    assert not modelo["visible"]
    assert not step["visible"]
    assert not csv["visible"]


def test_solicitud_declinada(monkeypatch):
    """Muestra la justificación y oculta archivos."""

    monkeypatch.setattr(
        ui,
        "consultar_api",
        lambda texto: {
            "resultado": "declinacion",
            "motivo": "Pieza fuera del catálogo",
        },
    )

    estado, modelo, step, csv = ui.procesar_solicitud("Diseñar una turbina")

    assert "Solicitud declinada" in estado
    assert "fuera del catálogo" in estado
    assert not modelo["visible"]
    assert not step["visible"]
    assert not csv["visible"]


def test_generacion_con_archivos(monkeypatch, directorio_salidas):
    """Comprueba el visor GLB y las descargas STEP y CSV."""

    for nombre in ("pieza.glb", "pieza.step", "materiales.csv"):
        (directorio_salidas / nombre).write_bytes(b"archivo-simulado")

    monkeypatch.setattr(
        ui,
        "consultar_api",
        lambda texto: {
            "resultado": "generada",
            "glb": "pieza.glb",
            "step": "pieza.step",
            "csv": "materiales.csv",
        },
    )

    estado, modelo, step, csv = ui.procesar_solicitud("Placa de 120 mm con 4 agujeros")

    assert "Diseño preliminar generado" in estado
    assert modelo["visible"]
    assert step["visible"]
    assert csv["visible"]

    assert modelo["value"].endswith("pieza.glb")
    assert step["value"].endswith("pieza.step")
    assert csv["value"].endswith("materiales.csv")


def test_error_de_conexion(monkeypatch):
    """Muestra un mensaje controlado cuando FastAPI no está disponible."""

    def api_no_disponible(texto):
        raise RuntimeError("No hay conexión con FastAPI")

    monkeypatch.setattr(ui, "consultar_api", api_no_disponible)

    estado, modelo, step, csv = ui.procesar_solicitud("Placa de 120 mm")

    assert "No hay conexión" in estado
    assert not modelo["visible"]
    assert not step["visible"]
    assert not csv["visible"]


def test_respuesta_desconocida(monkeypatch):
    """Rechaza formatos de respuesta inesperados."""

    monkeypatch.setattr(
        ui,
        "consultar_api",
        lambda texto: {"resultado": "desconocido"},
    )

    estado, modelo, step, csv = ui.procesar_solicitud("Placa de 120 mm")

    assert "no reconocida" in estado
    assert not modelo["visible"]
    assert not step["visible"]
    assert not csv["visible"]


def test_archivo_fuera_de_outputs(directorio_salidas):
    """Impide exponer archivos externos a outputs."""

    privado = directorio_salidas.parent / "privado.step"
    privado.write_bytes(b"contenido-privado")

    assert ui.archivo_seguro("../privado.step", ".step") is None
    assert ui.archivo_seguro(str(privado), ".step") is None


def test_archivo_con_extension_incorrecta(directorio_salidas):
    """Solo permite archivos con la extensión solicitada."""

    (directorio_salidas / "pieza.csv").write_text("material,cantidad")

    assert ui.archivo_seguro("pieza.csv", ".step") is None


def test_archivo_inexistente(directorio_salidas):
    """No ofrece descargas de archivos inexistentes."""

    assert ui.archivo_seguro("inexistente.step", ".step") is None


def test_consultar_api_respuesta_exitosa(monkeypatch):
    """Comprueba el envío correcto de solicitudes a FastAPI."""

    def simular_urlopen(solicitud, timeout):
        assert solicitud.method == "POST"
        assert solicitud.full_url.endswith("/generar")
        assert b"Placa de 120 mm" in solicitud.data
        assert timeout == 70

        return BytesIO(b'{"resultado": "declinacion", "motivo": "Fuera del catalogo"}')

    monkeypatch.setattr(ui, "urlopen", simular_urlopen)

    respuesta = ui.consultar_api("Placa de 120 mm")

    assert respuesta["resultado"] == "declinacion"
    assert respuesta["motivo"] == "Fuera del catalogo"


def test_consultar_api_error_http(monkeypatch):
    """Comprueba que los errores HTTP se comuniquen correctamente."""

    def simular_error(solicitud, timeout):
        raise HTTPError(
            url=solicitud.full_url,
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=BytesIO(b'{"detail": "Pipeline CAD no disponible"}'),
        )

    monkeypatch.setattr(ui, "urlopen", simular_error)

    with pytest.raises(RuntimeError, match="Pipeline CAD no disponible"):
        ui.consultar_api("Placa de 120 mm")


def test_consultar_api_error_de_red(monkeypatch):
    """Comprueba el manejo de fallos de conexión HTTP."""

    def simular_error(solicitud, timeout):
        raise OSError("Sin conexion")

    monkeypatch.setattr(ui, "urlopen", simular_error)

    with pytest.raises(RuntimeError, match="No hay conexión"):
        ui.consultar_api("Placa de 120 mm")


def test_creacion_de_interfaz():
    """Comprueba que Gradio construya la interfaz correctamente."""

    demo = ui.crear_interfaz()

    assert isinstance(demo, ui.gr.Blocks)


def test_sin_glb_con_step_disponible(monkeypatch, directorio_salidas):
    """Permite descargar STEP aunque no exista el GLB."""
    (directorio_salidas / "pieza.step").write_bytes(b"step")

    monkeypatch.setattr(
        ui,
        "consultar_api",
        lambda texto: {
            "resultado": "generada",
            "glb": None,
            "step": "pieza.step",
            "csv": None,
        },
    )

    estado, modelo, step, csv = ui.procesar_solicitud("Placa metálica")

    assert not modelo["visible"]
    assert step["visible"]
    assert not csv["visible"]
    assert "vista 3D no está disponible" in estado


def test_glb_disponible_sin_step(monkeypatch, directorio_salidas):
    """Advierte cuando existe GLB pero falta STEP."""
    (directorio_salidas / "pieza.glb").write_bytes(b"glb")

    monkeypatch.setattr(
        ui,
        "consultar_api",
        lambda texto: {
            "resultado": "generada",
            "glb": "pieza.glb",
            "step": None,
            "csv": None,
        },
    )

    estado, modelo, step, csv = ui.procesar_solicitud("Placa metálica")

    assert modelo["visible"]
    assert not step["visible"]
    assert not csv["visible"]
    assert "no hay archivo STEP disponible" in estado


def test_error_muestra_url_configurada(monkeypatch):
    """El mensaje de conexión utiliza la URL real de FastAPI."""
    monkeypatch.setattr(ui, "API_URL", "http://127.0.0.1:8011")

    def simular_error(solicitud, timeout):
        raise OSError("Sin conexión")

    monkeypatch.setattr(ui, "urlopen", simular_error)

    with pytest.raises(RuntimeError, match="127.0.0.1:8011"):
        ui.consultar_api("Placa de 120 mm")


def test_crear_interfaz_crea_outputs(monkeypatch, tmp_path):
    """Gradio crea outputs incluso si no existe inicialmente."""
    salidas = tmp_path / "outputs"
    monkeypatch.setattr(ui, "SALIDAS", salidas)

    ui.crear_interfaz()

    assert salidas.is_dir()


def test_rechaza_nombre_archivo_invalido(directorio_salidas):
    """No acepta nombres de archivo vacíos o de tipo incorrecto."""
    assert ui.archivo_seguro(None, ".step") is None
    assert ui.archivo_seguro(123, ".step") is None
    assert ui.archivo_seguro("", ".step") is None


def test_error_http_con_detalle_estructurado(monkeypatch):
    """Convierte los errores HTTP estructurados en mensajes legibles."""
    from io import BytesIO
    from urllib.error import HTTPError

    def simular_error(solicitud, timeout):
        raise HTTPError(
            url=solicitud.full_url,
            code=422,
            msg="Validation Error",
            hdrs=None,
            fp=BytesIO(b'{"detail": [{"loc": ["body", "texto"]}]}'),
        )

    monkeypatch.setattr(ui, "urlopen", simular_error)

    with pytest.raises(RuntimeError, match="Solicitud inválida"):
        ui.consultar_api("Placa de 120 mm")


def test_respuesta_real_pipeline(monkeypatch, directorio_salidas):
    """Valida la respuesta del pipeline con la clave bom_csv."""
    for nombre in ("pieza.step", "pieza.glb", "materiales.csv"):
        (directorio_salidas / nombre).write_bytes(b"archivo-simulado")

    monkeypatch.setattr(
        ui,
        "consultar_api",
        lambda texto: {
            "step": "pieza.step",
            "glb": "pieza.glb",
            "bom_csv": "materiales.csv",
        },
    )

    estado, modelo, step, csv = ui.procesar_solicitud("Placa de 120 mm con 4 agujeros")

    assert "Diseño preliminar generado" in estado
    assert modelo["visible"]
    assert step["visible"]
    assert csv["visible"]
    assert csv["value"].endswith("materiales.csv")


def test_declinacion_real_http_422(monkeypatch):
    """Verifica que una declinación HTTP 422 muestre su motivo."""
    from io import BytesIO
    from urllib.error import HTTPError

    def simular_declinacion(solicitud, timeout):
        raise HTTPError(
            url=solicitud.full_url,
            code=422,
            msg="Unprocessable Content",
            hdrs=None,
            fp=BytesIO(b'{"detail": "Pieza declinada: Fuera del catalogo CAD"}'),
        )

    monkeypatch.setattr(ui, "urlopen", simular_declinacion)

    estado, modelo, step, csv = ui.procesar_solicitud("Diseñar una pieza fuera del catálogo")

    assert "Solicitud declinada" in estado
    assert "Fuera del catalogo CAD" in estado
    assert not modelo["visible"]
    assert not step["visible"]
    assert not csv["visible"]


def test_consultar_api_timeout_configurable(monkeypatch):
    """Comprueba que la API utilice el timeout configurado."""
    from io import BytesIO

    monkeypatch.setattr(ui, "API_TIMEOUT", 25)

    def simular_urlopen(solicitud, timeout):
        assert timeout == 25
        return BytesIO(b'{"resultado": "declinacion"}')

    monkeypatch.setattr(ui, "urlopen", simular_urlopen)

    respuesta = ui.consultar_api("Placa de 120 mm")

    assert respuesta["resultado"] == "declinacion"
