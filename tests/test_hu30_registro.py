"""SPEC-031 AC1/AC2: pruebas de concurrencia y backup sin motor CAD."""

import csv
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from m2_cad.persistencia_registro import backup, restore
from m2_cad.registro import CAMPOS, registrar


def _registro(ruta, identificador, texto="Placa metálica"):
    return registrar(
        texto=texto,
        traduccion="no aplica",
        resultado={"step": "simulado.step"},
        latencia_ms=10.0,
        ruta=ruta,
        identificador=identificador,
    )


def test_ac1_80_solicitudes_simultaneas_sin_perdidas(tmp_path):
    ruta = tmp_path / "registro.csv"
    ids = [uuid.uuid4().hex for _ in range(80)]
    with ThreadPoolExecutor(max_workers=16) as pool:
        filas = list(pool.map(lambda identificador: _registro(ruta, identificador), ids))
    with ruta.open(newline="", encoding="utf-8") as archivo:
        almacenadas = list(csv.DictReader(archivo))
    assert len(filas) == len(almacenadas) == 80
    assert {f["id"] for f in almacenadas} == set(ids)
    assert all(list(f) == CAMPOS and all(f.values()) for f in almacenadas)


def test_ac1_id_repetido_conserva_primera_fila(tmp_path):
    ruta = tmp_path / "registro.csv"
    identificador = uuid.uuid4().hex
    primera = _registro(ruta, identificador, "Primera solicitud")
    segunda = _registro(ruta, identificador, "Segunda solicitud")
    assert primera == segunda
    with ruta.open(newline="", encoding="utf-8") as archivo:
        assert len(list(csv.DictReader(archivo))) == 1


def test_ac1_duplicados_concurrentes_son_idempotentes(tmp_path):
    ruta = tmp_path / "registro.csv"
    identificador = uuid.uuid4().hex
    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(lambda _: _registro(ruta, identificador), range(50)))
    with ruta.open(newline="", encoding="utf-8") as archivo:
        assert len(list(csv.DictReader(archivo))) == 1


def test_registro_conserva_sanitizacion(tmp_path):
    fila = _registro(
        tmp_path / "registro.csv",
        uuid.uuid4().hex,
        "Me llamo Juan Pérez y escribí a juan@ejemplo.com",
    )
    assert "juan@" not in fila["texto"]
    assert "Juan Pérez" not in fila["texto"]
    assert all(fila.values())


def test_ac2_restore_byte_a_byte(tmp_path):
    ruta = tmp_path / "registro.csv"
    destino = tmp_path / "backups" / "registro.csv"
    _registro(ruta, uuid.uuid4().hex)
    _registro(ruta, uuid.uuid4().hex)
    original = ruta.read_bytes()
    assert backup(ruta, destino) == destino
    _registro(ruta, uuid.uuid4().hex)
    assert ruta.read_bytes() != original
    assert restore(ruta, destino) == ruta
    assert ruta.read_bytes() == original


def test_ac2_backup_no_sobrescribe(tmp_path):
    ruta = tmp_path / "registro.csv"
    respaldo = tmp_path / "backup.csv"
    _registro(ruta, uuid.uuid4().hex)
    backup(ruta, respaldo)
    with pytest.raises(FileExistsError):
        backup(ruta, respaldo)


def test_ac2_restore_rechaza_csv_invalido(tmp_path):
    ruta = tmp_path / "registro.csv"
    respaldo = tmp_path / "backup.csv"
    _registro(ruta, uuid.uuid4().hex)
    original = ruta.read_bytes()
    respaldo.write_text("columna,incorrecta\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        restore(ruta, respaldo)
    assert ruta.read_bytes() == original
