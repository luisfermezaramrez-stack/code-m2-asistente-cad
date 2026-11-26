"""HU-45: cola persistente, reanudación y worker separado (SPEC-046)."""

import asyncio
import csv
import json
import os
import secrets
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import date
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from m2_cad import api, seguimiento
from m2_cad.cola_trabajos import ColaTrabajos, TrabajoPersistido
from m2_cad.control import ControlGeneracion
from m2_cad.control_uso import ConfiguracionUso, ControlUso
from m2_cad.registro import SIN_TRADUCCION, registrar
from m2_cad.worker import consumir, ejecutar

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def cola_tmp(monkeypatch, tmp_path):
    """Cola y registro aislados; el procesador real se habilita sólo aquí."""
    ruta = tmp_path / "cola.json"
    registro = tmp_path / "registro.csv"
    monkeypatch.setenv("M2_COLA_HABILITADA", "1")
    monkeypatch.setenv("M2_COLA_PATH", str(ruta))
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", secrets.token_hex(32))
    monkeypatch.setenv("MLFLOW_TRACKING_ENABLED", "0")
    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: registro)
    cola = ColaTrabajos(ruta, propietario="api-prueba")
    monkeypatch.setattr(api, "cola_trabajos", cola)
    api.app.dependency_overrides[api.obtener_cola_trabajos] = lambda: cola
    yield cola, registro, ruta
    api.app.dependency_overrides.pop(api.obtener_cola_trabajos, None)


def _configuracion() -> dict:
    return asdict(seguimiento.Configuracion(activo=False))


def procesar_simulado(
    texto: str, control: ControlGeneracion, medido: dict | None = None
) -> dict[str, str]:
    """Procesador sin red, API key ni GPU; informa las etapas reales."""
    control.informar("validando")
    control.informar("generando")
    if medido is not None:
        medido["tokens_entrada"] = 10
        medido["tokens_salida"] = 4
    return {"resultado": "pieza.step", "texto": texto}


def _finalizador(registro: Path):
    llamadas: list[str] = []

    def finalizar(trabajo, terminal, medido, configuracion, ruta):
        llamadas.append(trabajo["id"])
        registrar(
            texto=trabajo["texto"],
            traduccion=SIN_TRADUCCION,
            resultado=terminal.get("resultado"),
            latencia_ms=1.0,
            error=terminal.get("motivo"),
            version="simulada",
            ruta=registro,
            identificador=trabajo["id"],
        )

    return finalizar, llamadas


def test_ac1_reinicio_sin_perdida_y_registro_no_duplicado(cola_tmp):
    """Un trabajo en curso se reanuda y su fila de registro sigue siendo única."""
    cola, registro, ruta = cola_tmp
    trabajo = cola.encolar(
        "soporte para bandeja", configuracion=_configuracion(), ruta_registro=registro
    )

    # Worker caído después de reclamar, antes de publicar el primer evento.
    assert cola.reclamar()["id"] == trabajo.id
    assert cola.estado(trabajo.id)["estado"] == "iniciando"

    reiniciada = ColaTrabajos(ruta, propietario="worker-reiniciado")
    assert reiniciada.reanudar() == 1
    reclamado = reiniciada.reclamar()
    assert reclamado is not None
    finalizar, llamadas = _finalizador(registro)

    estado = ejecutar(
        reclamado,
        procesar_simulado,
        reiniciada,
        ruta_registro=registro,
        finalizador=finalizar,
    )

    assert estado["estado"] == "verificado"
    assert estado["terminal"] is True
    assert reiniciada.reanudar() == 0
    assert llamadas == [trabajo.id]

    # Una reanudación repetida no añade una segunda fila (RNF-3).
    registrar(
        texto="soporte para bandeja",
        traduccion=SIN_TRADUCCION,
        resultado={"resultado": "pieza.step"},
        latencia_ms=1.0,
        ruta=registro,
        identificador=trabajo.id,
    )
    with registro.open(encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    assert len(filas) == 1
    assert filas[0]["id"] == trabajo.id


def test_finalizador_por_defecto_registra_y_guarda_medicion(cola_tmp):
    """El worker sin inyecciones usa el finalizador real con MLflow desactivado."""
    cola, registro, _ = cola_tmp
    trabajo = cola.encolar(
        "soporte para bandeja", configuracion=_configuracion(), ruta_registro=registro
    )
    reclamado = cola.reclamar()
    assert reclamado is not None

    estado = ejecutar(reclamado, procesar_simulado, cola, ruta_registro=registro)

    assert estado["estado"] == "verificado"
    with registro.open(encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    assert len(filas) == 1
    assert filas[0]["id"] == trabajo.id

    persistido = json.loads(cola.ruta.read_text(encoding="utf-8"))["trabajos"][trabajo.id]
    assert persistido["registrado"] is True
    assert persistido["medicion"]["tokens_entrada"] == 10


class _ClienteConectado:
    async def is_disconnected(self) -> bool:
        return False


def test_ac2_drenaje_no_corta_eventos(cola_tmp):
    """Tras cerrar la cola, el flujo SSE termina en un evento completo."""
    cola, registro, _ = cola_tmp
    trabajo = cola.encolar(
        "soporte para bandeja", configuracion=_configuracion(), ruta_registro=registro
    )
    nota = "x" * 2048

    def publicar() -> None:
        time.sleep(0.05)
        cola.publicar_evento(trabajo.id, "validando")
        time.sleep(0.05)
        cola.cerrar()
        cola.publicar_evento(trabajo.id, "generando")
        time.sleep(0.05)
        cola.publicar_evento(
            trabajo.id, "verificado", resultado={"resultado": "pieza.step", "nota": nota}
        )

    hilo = Thread(target=publicar)
    hilo.start()

    async def leer():
        datos: list[dict] = []
        async for bloque in TrabajoPersistido(cola, trabajo.id).eventos(_ClienteConectado()):
            linea = next(
                (linea for linea in bloque.splitlines() if linea.startswith("data: ")), None
            )
            if linea is not None:
                datos.append(json.loads(linea.removeprefix("data: ")))
        return datos

    eventos = asyncio.run(leer())
    hilo.join(timeout=5)

    assert [evento["estado"] for evento in eventos] == ["validando", "generando", "verificado"]
    assert eventos[-1]["terminal"] is True
    assert eventos[-1]["resultado"]["nota"] == nota
    with pytest.raises(HTTPException) as exc:
        cola.encolar("nueva", configuracion=_configuracion(), ruta_registro=registro)
    assert exc.value.status_code == 503


def test_ac3_worker_separado_del_proceso_api(cola_tmp, monkeypatch):
    """El trabajo se ejecuta en otro PID y el CSV se escribe desde el worker."""
    cola, registro, ruta = cola_tmp
    marcador = ruta.parent / "worker.pid"
    monkeypatch.setenv("M2_WORKER_MARKER", str(marcador))
    trabajo = cola.encolar(
        "soporte para bandeja", configuracion=_configuracion(), ruta_registro=registro
    )

    resultado = subprocess.run(
        [
            sys.executable,
            "-m",
            "m2_cad.worker",
            "--cola",
            str(ruta),
            "--procesador",
            "tests.worker_stub:procesar",
            "--registro",
            str(registro),
            "--una-vez",
            "--intervalo",
            "0.01",
        ],
        cwd=RAIZ,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert int(marcador.read_text(encoding="utf-8")) != os.getpid()
    assert "1 trabajos procesados" in resultado.stdout

    estado = cola.estado(trabajo.id)
    assert estado["estado"] == "verificado"
    assert estado["terminal"] is True
    with registro.open(encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    assert len(filas) == 1


def test_api_sse_encola_sin_ejecutar_el_pipeline(cola_tmp):
    """La ruta SSE de la API entrega el trabajo a la cola, no lo procesa."""
    cola, _, _ = cola_tmp
    with TestClient(api.app) as cliente:
        with cliente.stream(
            "POST",
            "/v1/generar",
            json={"texto": "soporte para bandeja"},
            headers={"Accept": "text/event-stream"},
        ) as respuesta:
            assert respuesta.status_code == 200
            identificador = respuesta.headers["x-registro-id"]
            estado = cola.estado(identificador)
            assert estado["estado"] == "iniciando"
            assert estado["terminal"] is False
            assert respuesta.headers["cache-control"] == "no-store, no-transform"


def test_consultar_y_cancelar_generacion_usan_la_cola(cola_tmp):
    """Los endpoints heredados consultan y cancelan trabajos persistidos (RNF-1)."""
    cola, registro, _ = cola_tmp
    trabajo = cola.encolar(
        "soporte para bandeja", configuracion=_configuracion(), ruta_registro=registro
    )
    with TestClient(api.app) as cliente:
        consulta = cliente.get(f"/v1/generaciones/{trabajo.id}")
        assert consulta.status_code == 200
        assert consulta.json()["estado"] == "iniciando"

        cancelacion = cliente.delete(f"/v1/generaciones/{trabajo.id}")
        assert cancelacion.status_code == 202
        assert cancelacion.json()["cancelacion_solicitada"] is True


SSE = {"Accept": "text/event-stream"}


@pytest.fixture
def api_con_cola_y_uso(cola_tmp):
    """API con cola activa, worker en un hilo y control de uso aislado (HU-32 × HU-45)."""
    cola, _, ruta = cola_tmp
    control = ControlUso()
    configuracion = seguimiento.Configuracion(activo=False, precio_entrada=1.0, precio_salida=2.0)
    api.app.dependency_overrides[api.obtener_control_uso] = lambda: control
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: configuracion
    try:
        with TestClient(api.app) as cliente:
            worker = Thread(
                target=consumir,
                args=(cola, procesar_simulado),
                kwargs={"intervalo": 0.01, "finalizador": lambda *_: None},
                daemon=True,
            )
            worker.start()
            yield SimpleNamespace(cliente=cliente, cola=cola, control=control, ruta=ruta)
            cola.cerrar()
            worker.join(timeout=5)
    finally:
        api.app.dependency_overrides.pop(api.obtener_control_uso, None)
        api.app.dependency_overrides.pop(api.obtener_configuracion_seguimiento, None)


def test_hu32_gasto_encolado_cuenta_una_vez_y_activa_el_presupuesto(api_con_cola_y_uso):
    """El costo que mide el worker llega al presupuesto y a /v1/uso una sola vez."""
    # Arrange
    sim = api_con_cola_y_uso
    costo = seguimiento.costo_usd(10, 4, precio_entrada=1.0, precio_salida=2.0)

    # Act
    respuesta = sim.cliente.post("/v1/generar", json={"texto": "soporte"}, headers=SSE)
    sim.control.configuracion = ConfiguracionUso(presupuesto_diario_usd=costo / 2)
    rechazo = sim.cliente.post("/v1/generar", json={"texto": "otro soporte"}, headers=SSE)
    primera = sim.cliente.get("/v1/uso").json()
    segunda = sim.cliente.get("/v1/uso").json()

    # Assert
    assert respuesta.status_code == 200
    assert sim.cola.estado(respuesta.headers["x-registro-id"])["estado"] == "verificado"
    assert rechazo.status_code == 429
    assert rechazo.headers["X-Limite-Tipo"] == "presupuesto"
    assert primera["costo_usd"] == pytest.approx(costo)
    assert primera["generaciones"] == 1
    assert segunda == primera
    assert len(json.loads(sim.ruta.read_text(encoding="utf-8"))["trabajos"]) == 1


def test_hu32_idempotencia_repite_el_trabajo_encolado(api_con_cola_y_uso):
    """Repetir la clave devuelve el trabajo de la cola, sin encolar otro (AC2)."""
    # Arrange
    sim = api_con_cola_y_uso
    cabeceras = {**SSE, "Idempotency-Key": "pedido-cola"}

    # Act
    original = sim.cliente.post("/v1/generar", json={"texto": "soporte"}, headers=cabeceras)
    repetida = sim.cliente.post("/v1/generar", json={"texto": "soporte"}, headers=cabeceras)

    # Assert
    identificador = original.headers["x-registro-id"]
    assert repetida.status_code == 200
    assert repetida.headers["Idempotent-Replay"] == "true"
    assert repetida.headers["X-Solicitud-ID"] == identificador
    assert repetida.json()["solicitud_id"] == identificador
    assert repetida.json()["estado"] == "verificado"
    assert len(json.loads(sim.ruta.read_text(encoding="utf-8"))["trabajos"]) == 1


def test_hu32_gasto_encolado_se_atribuye_al_dia_en_que_termino(cola_tmp):
    """Un trabajo terminado ayer no infla el gasto de hoy al contabilizarse tarde."""
    # Arrange
    cola, registro, _ = cola_tmp
    trabajo = cola.encolar("soporte", configuracion=_configuracion(), ruta_registro=registro)
    cola.guardar_medicion(trabajo.id, {"tokens_entrada": 10, "tokens_salida": 4})
    cola.publicar_evento(trabajo.id, "verificado", resultado={})
    with cola._editar() as datos:  # Simula un trabajo que terminó el día anterior.
        datos["trabajos"][trabajo.id]["actualizado_en"] = "2026-11-24T23:59:00+00:00"

    # Act
    pendientes = cola.tomar_gastos_pendientes()

    # Assert
    assert [pendiente["dia"] for pendiente in pendientes] == [date(2026, 11, 24)]
    assert pendientes[0]["medicion"] == {"tokens_entrada": 10, "tokens_salida": 4}
    assert cola.tomar_gastos_pendientes() == []
