"""HU-47 AC1-AC4: validación local del despliegue cloud, sin red ni secretos."""

import importlib.util
from pathlib import Path

RUTA = Path(__file__).resolve().parents[1] / "scripts" / "verify_hu47_cloud_config.py"
especificacion = importlib.util.spec_from_file_location("verify_hu47_cloud_config", RUTA)
validador = importlib.util.module_from_spec(especificacion)
especificacion.loader.exec_module(validador)


def entorno_valido(monkeypatch) -> None:
    """Fija variables simuladas con la forma que exige la validación."""
    monkeypatch.setenv("M2_IMAGE", "registro.interno/m2-cad:abc123")
    monkeypatch.setenv("M2_DOMAIN", "cad.ejemplo.example")
    monkeypatch.setenv("M2_TLS_EMAIL", "admin@ejemplo.example")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk" + "-simulada-123456")
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", "b" * 32)
    monkeypatch.setenv("M2_AUTH_SECRET", "a" * 32)
    monkeypatch.setenv("M2_AUTH_USERS", '{"operador":"pbkdf2_sha256$100000$abc$def"}')


def test_plantilla_valida_lista_lo_pendiente_sin_consultar_red(capsys):
    codigo = validador.main(["--modo", "plantilla"])

    salida = capsys.readouterr().out
    assert codigo == 0
    assert "Configuración cloud consistente" in salida
    assert "Pendiente para publicar" in salida
    assert "DNS del dominio propio" in salida


def test_la_api_no_publica_puertos_y_el_worker_espera_salud(capsys):
    compose = validador.leer(validador.COMPOSE)

    api = validador.bloque_servicio(compose, "m2-cad")
    worker = validador.bloque_servicio(compose, "m2-cad-worker")
    assert "ports:" not in api
    assert "condition: service_healthy" in worker
    assert "m2-cad-data:/app/data" in api
    assert "m2-cad-outputs:/app/outputs" in worker


def test_rechaza_dominio_con_esquema(monkeypatch, capsys):
    entorno_valido(monkeypatch)
    monkeypatch.setenv("M2_DOMAIN", "https://cad.ejemplo.example")

    codigo = validador.main(["--modo", "produccion"])

    salida = capsys.readouterr().out
    assert codigo == 1
    assert "M2_DOMAIN" in salida


def test_rechaza_secreto_corto_sin_imprimirlo(monkeypatch, capsys):
    entorno_valido(monkeypatch)
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", "secretoCortoUnicoXYZ")

    codigo = validador.main(["--modo", "produccion"])

    salida = capsys.readouterr().out
    assert codigo == 1
    assert "M2_DOWNLOAD_SECRET" in salida
    assert "secretoCortoUnicoXYZ" not in salida


def test_acepta_configuracion_de_produccion_simulada(monkeypatch, capsys):
    entorno_valido(monkeypatch)

    codigo = validador.main(["--modo", "produccion"])

    salida = capsys.readouterr().out
    assert codigo == 0
    assert "Configuración cloud consistente" in salida
    assert "No se hizo red" not in salida
