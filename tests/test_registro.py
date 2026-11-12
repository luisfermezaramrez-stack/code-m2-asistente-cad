"""Pruebas del registro de solicitudes (HU-06, parte de Luis Meza).

Cubre AC3 (0 campos vacíos en 20 llamadas) y AC4 (excluye nombres y correos,
Ley 1581 de 2012), además de los casos borde de la especificación
specs/004-registro-solicitudes/spec.md.
"""

import csv

import pytest

from m2_cad.registro import CAMPOS, RUTA_DEFAULT, registrar


def leer_registro(ruta):
    """Lee el CSV de registro como lista de diccionarios."""
    with open(ruta, newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def test_campos_definidos():
    """El registro define exactamente los 8 campos de la especificación."""
    assert CAMPOS == [
        "id",
        "hora",
        "texto",
        "traduccion",
        "resultado",
        "latencia_ms",
        "error",
        "version",
    ]


def test_registrar_fila_completa(tmp_path):
    """Cada solicitud se registra con los 8 campos (AC3, escenario 1)."""
    ruta = tmp_path / "registro.csv"

    fila = registrar(
        texto="Placa de 120 mm con 4 agujeros",
        traduccion="Plate of 120 mm with 4 holes",
        resultado={"ok": True},
        latencia_ms=125.4,
        version="gemma-3-12b-q6k",
        ruta=ruta,
    )

    assert fila["texto"] == "Placa de 120 mm con 4 agujeros"
    assert fila["traduccion"] == "Plate of 120 mm with 4 holes"
    assert fila["resultado"]
    assert fila["latencia_ms"] == "125.4"
    assert fila["version"] == "gemma-3-12b-q6k"
    assert fila["error"]  # sin error queda con valor conocido, no vacío
    assert fila["id"]
    assert fila["hora"]


def test_id_y_hora_unicos(tmp_path):
    """Cada fila tiene id propio y hora ISO 8601 (FR-004: trazabilidad)."""
    ruta = tmp_path / "registro.csv"

    fila_1 = registrar(texto="a", traduccion="a", resultado={}, latencia_ms=1, ruta=ruta)
    fila_2 = registrar(texto="b", traduccion="b", resultado={}, latencia_ms=2, ruta=ruta)

    assert fila_1["id"] != fila_2["id"]
    assert "T" in fila_1["hora"]  # formato ISO 8601


def test_veinte_llamadas_sin_campos_vacios(tmp_path):
    """En 20 llamadas, 0 campos vacíos en el registro (AC3 / FR-002)."""
    ruta = tmp_path / "registro.csv"

    for i in range(20):
        registrar(
            texto=f"Solicitud {i} de 30 mm",
            traduccion=f"Request {i} of 30 mm",
            resultado={"ok": True},
            latencia_ms=10 + i,
            ruta=ruta,
        )

    filas = leer_registro(ruta)
    assert len(filas) == 20
    for fila in filas:
        assert set(fila.keys()) == set(CAMPOS)
        for campo in CAMPOS:
            assert fila[campo] != "", f"campo vacío: {campo} en fila {fila['id']}"


def test_error_queda_registrado_y_fila_conocida(tmp_path):
    """Si la llamada falla a mitad de proceso, error captura el fallo y los
    demás campos quedan con valores conocidos (caso borde de la spec)."""
    ruta = tmp_path / "registro.csv"

    fila = registrar(
        texto="Placa de 120 mm",
        traduccion="Plate of 120 mm",
        resultado=None,
        latencia_ms=40,
        error="Timeout del modelo",
        ruta=ruta,
    )

    assert fila["error"] == "Timeout del modelo"
    for campo in CAMPOS:
        assert fila[campo] != ""


def test_version_ausente_registra_desconocida(tmp_path):
    """Si el modelo no reporta versión, se registra 'desconocida' (caso borde)."""
    ruta = tmp_path / "registro.csv"

    fila = registrar(
        texto="Placa de 120 mm",
        traduccion="Plate of 120 mm",
        resultado={"ok": True},
        latencia_ms=10,
        version=None,
        ruta=ruta,
    )

    assert fila["version"] == "desconocida"


@pytest.mark.parametrize(
    "texto",
    [
        "Contacto: juan.perez@example.com para la pieza de 120 mm",
        "Escribime a soporte-cad@unia.edu.co antes de cortar la placa",
    ],
)
def test_excluye_correos(tmp_path, texto):
    """El registro no guarda correos (AC4 / FR-003, Ley 1581)."""
    ruta = tmp_path / "registro.csv"

    fila = registrar(
        texto=texto,
        traduccion="traduccion",
        resultado={"ok": True},
        latencia_ms=5,
        ruta=ruta,
    )

    assert "@" not in fila["texto"]
    assert "[correo eliminado]" in fila["texto"]


@pytest.mark.parametrize(
    "texto",
    [
        "Me llamo Juan Pérez y quiero una placa de 120 mm",
        "Mi nombre es María González, corta el soporte de 30 mm",
        "Soy Carlos Ruiz y necesito 4 agujeros de 8 mm",
    ],
)
def test_excluye_nombres_declarados(tmp_path, texto):
    """El registro no guarda nombres declarados por el usuario (AC4 / FR-003)."""
    ruta = tmp_path / "registro.csv"

    fila = registrar(
        texto=texto,
        traduccion="traduccion",
        resultado={"ok": True},
        latencia_ms=5,
        ruta=ruta,
    )

    assert "Pérez" not in fila["texto"]
    assert "González" not in fila["texto"]
    assert "Ruiz" not in fila["texto"]
    assert "[nombre eliminado]" in fila["texto"]


def test_la_sanitizacion_llega_a_todos_los_campos(tmp_path):
    """Nombres y correos se excluyen de texto, traduccion y resultado (AC4)."""
    ruta = tmp_path / "registro.csv"

    fila = registrar(
        texto="Placa para ana.lopez@example.com",
        traduccion="Plate for ana.lopez@example.com",
        resultado={"nota": "contacto: soporte@unia.edu.co"},
        latencia_ms=5,
        ruta=ruta,
    )

    assert "@" not in fila["texto"]
    assert "@" not in fila["traduccion"]
    assert "@" not in fila["resultado"]


def test_ruta_default_apunta_a_data():
    """El registro por defecto vive en data/registro.csv (plan de HU-06)."""
    assert RUTA_DEFAULT.as_posix() == "data/registro.csv"
