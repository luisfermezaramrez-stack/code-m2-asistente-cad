"""HU-32 (SPEC-033): presupuesto, idempotencia, ventana y gasto acumulado.

Toda la generación se simula: sin red, API key, GPU ni servicios externos.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from m2_cad.control_uso import ConfiguracionUso, ControlUso, RegistroIdempotencia


@pytest.fixture
def api_simulado(tmp_path, monkeypatch):
    """API aislada con un control nuevo, precios fijos y processor contable."""
    from m2_cad import api, seguimiento

    monkeypatch.setenv("M2_DOWNLOAD_SECRET", "hu32-secreto-" * 6)  # efímero, sin red
    control = ControlUso()
    configuracion = seguimiento.Configuracion(activo=False, precio_entrada=1.0, precio_salida=2.0)
    llamadas = {"modelo": 0}

    def procesador(texto: str, medicion: dict | None = None) -> dict[str, str]:
        llamadas["modelo"] += 1
        if medicion is not None:
            medicion["tokens_entrada"] = 120
            medicion["tokens_salida"] = 40
        return {"resultado": "generada", "step": "pieza.step"}

    def procesador_sse(texto, control_generacion, medicion=None):
        control_generacion.informar("validando")
        control_generacion.informar("generando")
        return procesador(texto, medicion)

    dependencias = (
        api.obtener_procesador,
        api.obtener_procesador_sse,
        api.obtener_configuracion_seguimiento,
        api.obtener_control_uso,
    )
    api.app.dependency_overrides[dependencias[0]] = lambda: procesador
    api.app.dependency_overrides[dependencias[1]] = lambda: procesador_sse
    api.app.dependency_overrides[dependencias[2]] = lambda: configuracion
    api.app.dependency_overrides[dependencias[3]] = lambda: control
    monkeypatch.setattr(api, "RUTA_DEFAULT", tmp_path / "registro.csv")

    with TestClient(api.app) as client:
        yield SimpleNamespace(client=client, control=control, llamadas=llamadas)

    for dependencia in dependencias:
        api.app.dependency_overrides.pop(dependencia, None)


def _generar(client: TestClient, texto: str = "Espaciador de 14 mm", **cabeceras):
    return client.post("/generar", json={"texto": texto}, headers=cabeceras)


def test_ac1_presupuesto_excedido_no_llama_al_modelo(api_simulado):
    """AC1: con el presupuesto agotado se rechaza antes de pagar tokens."""
    sim = api_simulado
    sim.control.configuracion = ConfiguracionUso(presupuesto_diario_usd=0.0001)
    sim.control.registrar_gasto(0.0002)

    respuesta = _generar(sim.client)

    assert respuesta.status_code == 429
    assert respuesta.headers["X-Limite-Tipo"] == "presupuesto"
    assert "Presupuesto diario" in respuesta.json()["detail"]
    assert sim.llamadas["modelo"] == 0
    assert sim.client.get("/uso").json()["costo_usd"] == pytest.approx(0.0002)


def test_ac2_idempotencia_no_duplica_gasto_ni_trabajo(api_simulado):
    """AC2: la misma clave devuelve la generación original sin repetirla."""
    sim = api_simulado
    cabeceras = {"Idempotency-Key": "clave-abc", "X-Session-ID": "sesion-1"}

    primera = _generar(sim.client, **cabeceras)
    segunda = _generar(sim.client, **cabeceras)

    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert segunda.json() == primera.json()
    assert segunda.headers["Idempotent-Replay"] == "true"
    assert segunda.headers["X-Registro-ID"] == primera.headers["X-Registro-ID"]
    assert sim.llamadas["modelo"] == 1
    uso = sim.client.get("/uso").json()
    assert uso["costo_usd"] == pytest.approx(0.0002)
    assert uso["generaciones"] == 1


def test_ac2_clave_reutilizada_con_otro_texto_conflicta(api_simulado):
    """RF-4: una clave no puede representar dos solicitudes distintas."""
    sim = api_simulado
    cabeceras = {"Idempotency-Key": "clave-abc", "X-Session-ID": "sesion-1"}
    assert _generar(sim.client, **cabeceras).status_code == 200

    conflicto = _generar(sim.client, texto="Soporte de 20 mm", **cabeceras)

    assert conflicto.status_code == 409
    assert conflicto.headers["X-Limite-Tipo"] == "idempotencia"
    assert sim.llamadas["modelo"] == 1


def test_ac3_limite_por_ventana_por_sesion(api_simulado):
    """AC3: la solicitud K+1 se rechaza; otra sesión conserva su cuota."""
    sim = api_simulado
    sim.control.configuracion = ConfiguracionUso(limite_ventana=2, ventana_segundos=60)
    cabeceras = {"X-Session-ID": "sesion-1"}

    assert _generar(sim.client, **cabeceras).status_code == 200
    assert _generar(sim.client, **cabeceras).status_code == 200
    rechazada = _generar(sim.client, **cabeceras)

    assert rechazada.status_code == 429
    assert rechazada.headers["X-Limite-Tipo"] == "ventana"
    assert int(rechazada.headers["Retry-After"]) > 0
    assert sim.llamadas["modelo"] == 2
    assert _generar(sim.client, **{"X-Session-ID": "sesion-2"}).status_code == 200
    assert sim.llamadas["modelo"] == 3


def test_ac4_gasto_acumulado_suma_costo_de_cada_generacion(api_simulado):
    """AC4: el agregado consultable suma el costo calculado por seguimiento."""
    sim = api_simulado

    assert _generar(sim.client, texto="Pieza A").status_code == 200
    assert _generar(sim.client, texto="Pieza B").status_code == 200

    uso = sim.client.get("/uso").json()
    assert uso["fecha"] == datetime.now(timezone.utc).date().isoformat()
    assert uso["moneda"] == "USD"
    assert uso["costo_usd"] == pytest.approx(0.0004)
    assert uso["generaciones"] == 2
    assert uso["presupuesto_diario_usd"] == 0
    assert uso["ventana_segundos"] == 60


def test_sin_topes_ni_clave_el_comportamiento_no_cambia(api_simulado):
    """RNF-2: sin configuración ni Idempotency-Key no aparecen cabeceras nuevas."""
    sim = api_simulado
    assert sim.client.get("/uso").json()["costo_usd"] == 0

    respuesta = _generar(sim.client)

    assert respuesta.status_code == 200
    assert "Idempotent-Replay" not in respuesta.headers
    assert sim.llamadas["modelo"] == 1


def test_reintento_sse_devuelve_estado_terminal(api_simulado):
    """RF-4 también aplica a SSE: se devuelve el estado del mismo trabajo."""
    sim = api_simulado
    cabeceras = {
        "Idempotency-Key": "clave-sse",
        "X-Session-ID": "sesion-1",
        "Accept": "text/event-stream",
    }

    primera = _generar(sim.client, **cabeceras)
    assert primera.status_code == 200
    solicitud_id = primera.headers["X-Registro-ID"]
    for _ in range(100):
        estado = sim.client.get(f"/generaciones/{solicitud_id}").json()
        if estado["terminal"]:
            break
        time.sleep(0.01)
    assert estado["terminal"] is True

    repetida = _generar(sim.client, **cabeceras)
    assert repetida.headers["Idempotent-Replay"] == "true"
    assert repetida.json()["solicitud_id"] == solicitud_id
    assert repetida.json()["estado"] == "verificado"
    assert sim.llamadas["modelo"] == 1


def test_configuracion_ignora_valores_invalidos():
    """Una variable mal escrita no desactiva el servicio por una excepción."""
    configuracion = ConfiguracionUso.desde_entorno(
        {
            "M2_LIMITE_SOLICITUDES_VENTANA": "muchas",
            "M2_VENTANA_SEGUNDOS": "0",
            "M2_PRESUPUESTO_DIARIO_USD": "-5",
        }
    )
    assert configuracion == ConfiguracionUso(limite_ventana=0, ventana_segundos=60)

    valida = ConfiguracionUso.desde_entorno(
        {
            "M2_LIMITE_SOLICITUDES_VENTANA": "3",
            "M2_VENTANA_SEGUNDOS": "15",
            "M2_PRESUPUESTO_DIARIO_USD": "0.25",
        }
    )
    assert valida == ConfiguracionUso(3, 15, 0.25)


def test_la_ventana_se_libera_al_cumplir_el_plazo():
    """Una vez vencida la ventana, la misma sesión vuelve a tener cuota."""
    ahora = [0.0]
    control = ControlUso(
        ConfiguracionUso(limite_ventana=1, ventana_segundos=10), reloj=lambda: ahora[0]
    )

    control.reservar("sesion-1")
    ahora[0] = 10.0
    control.reservar("sesion-1")

    assert control.gasto_acumulado()["limite_solicitudes_ventana"] == 1


def test_costo_invalido_y_sin_clave_no_contaminan_el_estado():
    """Valores no finitos se ignoran; sin clave no se guarda idempotencia."""
    control = ControlUso()
    control.registrar_gasto(float("nan"))
    registro = RegistroIdempotencia("id", "", "json")

    control.confirmar_idempotencia(None, registro, respuesta={"resultado": "generada"})
    control.liberar_idempotencia(None, registro)

    assert control.gasto_acumulado()["generaciones"] == 0
    assert registro.respuesta is None
