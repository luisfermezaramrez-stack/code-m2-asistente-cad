"""HU-15: transporte incremental, terminales y cancelación comprobable."""

import asyncio
import csv
import json
from threading import Event

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import ClientDisconnect, Request

from m2_cad import api
from m2_cad.seguimiento import SolicitudDeclinada
from m2_cad.trabajos import GestorTrabajos, RespuestaSSE, Trabajo


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    gestor = GestorTrabajos()
    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: tmp_path / "registro.csv")
    api.app.dependency_overrides[api.obtener_gestor_trabajos] = lambda: gestor
    yield gestor
    api.app.dependency_overrides.pop(api.obtener_gestor_trabajos, None)
    api.app.dependency_overrides.pop(api.obtener_procesador_sse, None)


def procesador(procesar):
    api.app.dependency_overrides[api.obtener_procesador_sse] = lambda: procesar


def leer_eventos(texto):
    return [
        json.loads(linea.removeprefix("data: "))
        for linea in texto.splitlines()
        if linea.startswith("data: ")
    ]


def test_sse_orden_terminal_y_contrato_json(entorno, tmp_path):
    def generar(texto, control):
        assert texto == "Placa de 120 mm"
        control.informar("validando")
        control.informar("generando")
        return {"step": "pieza.step", "aviso": "Diseño preliminar"}

    procesador(generar)
    with TestClient(api.app) as client:
        respuesta = client.post(
            "/generar", json={"texto": "Placa de 120 mm"}, headers={"Accept": "text/event-stream"}
        )
        assert client.get("/health").json() == {"status": "ok"}
        eventos = leer_eventos(respuesta.text)
        id_ = respuesta.headers["x-solicitud-id"]
        assert respuesta.status_code == 200
        assert respuesta.headers["content-type"].startswith("text/event-stream")
        assert respuesta.headers["x-accel-buffering"] == "no"
        assert [e["estado"] for e in eventos] == ["validando", "generando", "verificado"]
        assert [e["secuencia"] for e in eventos] == [1, 2, 3]
        assert all(e["solicitud_id"] == id_ for e in eventos)
        assert [e["terminal"] for e in eventos] == [False, False, True]
        assert eventos[-1]["resultado"]["step"] == "pieza.step"
        # Cancelar un resultado ya confirmado no lo reescribe.
        assert client.delete(f"/generaciones/{id_}").json()["estado"] == "verificado"
        assert not client.get(f"/generaciones/{id_}").json()["cancelacion_solicitada"]
    assert len((tmp_path / "registro.csv").read_text().splitlines()) == 2


@pytest.mark.parametrize(
    ("error", "estado", "codigo"),
    [
        (SolicitudDeclinada("Fuera del catálogo"), "declinado", 422),
        (HTTPException(422, "Geometría inválida"), "error", 422),
        (HTTPException(503, "Modelo no disponible"), "error", 503),
        (RuntimeError("detalle privado"), "error", 500),
    ],
)
def test_sse_errores_no_se_confunden_con_declinacion(entorno, error, estado, codigo):
    def fallar(texto, control):
        control.informar("validando")
        control.informar("generando")
        raise error

    procesador(fallar)
    with TestClient(api.app) as client:
        respuesta = client.post(
            "/generar", json={"texto": "Pieza"}, headers={"Accept": "text/event-stream"}
        )
    eventos = leer_eventos(respuesta.text)
    assert [e["estado"] for e in eventos] == ["validando", "generando", estado]
    assert eventos[-1]["terminal"] is True
    assert eventos[-1]["codigo_http"] == codigo
    assert "resultado" not in eventos[-1]
    assert "detalle privado" not in respuesta.text


def test_sse_entrada_invalida_conserva_422_sin_iniciar_trabajo(entorno):
    with TestClient(api.app) as client:
        respuesta = client.post(
            "/generar", json={"texto": " "}, headers={"Accept": "text/event-stream"}
        )
        assert respuesta.status_code == 422
        assert respuesta.headers["content-type"] == "application/json"
        assert client.get("/generaciones/desconocida").status_code == 404
        assert client.delete("/generaciones/desconocida").status_code == 404


def test_openapi_conserva_contrato_json_y_anuncia_sse():
    contenido = api.app.openapi()["paths"]["/generar"]["post"]["responses"]["200"]["content"]
    assert contenido["application/json"]["schema"]["additionalProperties"] == {"type": "string"}
    assert contenido["text/event-stream"]["schema"] == {"type": "string"}


def test_sse_sin_modelo_informa_validacion_y_error(entorno, monkeypatch):
    for variable in ("LLM_BASE_URL", "LLM_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    with TestClient(api.app) as client:
        respuesta = client.post(
            "/generar", json={"texto": "Placa"}, headers={"Accept": "text/event-stream"}
        )
    eventos = leer_eventos(respuesta.text)
    assert [e["estado"] for e in eventos] == ["validando", "error"]
    assert eventos[-1]["codigo_http"] == 503
    assert eventos[-1]["motivo"] == "El modelo no está configurado: falta DEEPSEEK_API_KEY."


@pytest.mark.parametrize("variable_clave", ["DEEPSEEK_API_KEY", "LLM_API_KEY"])
@pytest.mark.parametrize("salida", ["verificado", "declinado", "401", "429", "timeout"])
def test_hu14_sse_usa_espanol_y_clave_sin_url_y_registra_no_aplica(
    entorno, monkeypatch, tmp_path, variable_clave, salida
):
    """DeepSeek simulado en transporte; pipeline/SSE/registro y CAD reales."""
    from m2_cad import pipeline

    for variable in ("LLM_BASE_URL", "LLM_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    clave = "clave-solo-prueba-hu14"
    monkeypatch.setenv(variable_clave, clave)
    texto = "Espaciador de acero de 14 mm"
    llamadas = []

    def chat(cuerpo, *, url, timeout):
        llamadas.append(cuerpo)
        assert cuerpo["messages"][-1] == {"role": "user", "content": texto}
        assert "api.deepseek.com" in url
        request = httpx.Request("POST", url)
        if salida == "timeout":
            raise httpx.ReadTimeout(clave, request=request)
        if salida in {"401", "429"}:
            raise httpx.HTTPStatusError(
                clave, request=request, response=httpx.Response(int(salida), request=request)
            )
        programa = (
            {"unsupported": "turbina"}
            if salida == "declinado"
            else {"parts": [{"id": "p", "type": "spacer", "params": {}}], "mates": []}
        )
        return {"choices": [{"message": {"content": json.dumps(programa)}}]}

    monkeypatch.setattr(pipeline.llm, "chat", chat)
    monkeypatch.chdir(tmp_path)
    with TestClient(api.app) as client:
        respuesta = client.post(
            "/generar", json={"texto": texto}, headers={"Accept": "text/event-stream"}
        )
    eventos = leer_eventos(respuesta.text)
    esperado = salida if salida in {"verificado", "declinado"} else "error"
    assert [e["estado"] for e in eventos] == ["validando", "generando", esperado]
    assert len(llamadas) == 1
    assert clave not in respuesta.text
    assert "traduccion" not in eventos[-1].get("resultado", {})
    if esperado == "error":
        assert eventos[-1]["codigo_http"] == 503
    registro = (tmp_path / "registro.csv").read_text(encoding="utf-8")
    assert clave not in registro
    assert list(csv.DictReader(registro.splitlines()))[0]["traduccion"] == "no aplica"


class ConexionASGI:
    """Cliente sin buffering: observa eventos antes de que el procesador termine."""

    def __init__(self):
        self.entrada = asyncio.Queue()
        self.salida = asyncio.Queue()

    async def abrir(self):
        await self.entrada.put(
            {
                "type": "http.request",
                "body": b'{"texto":"Placa"}',
                "more_body": False,
            }
        )
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/generar",
            "raw_path": b"/generar",
            "query_string": b"",
            "root_path": "",
            "headers": [(b"content-type", b"application/json"), (b"accept", b"text/event-stream")],
            "client": ("test", 1234),
            "server": ("test", 80),
        }
        self.tarea = asyncio.create_task(api.app(scope, self.entrada.get, self.salida.put))
        inicio = await asyncio.wait_for(self.salida.get(), 5)
        assert inicio["type"] == "http.response.start" and inicio["status"] == 200
        self.id = dict(inicio["headers"])[b"x-solicitud-id"].decode()
        return self

    async def evento(self):
        mensaje = await asyncio.wait_for(self.salida.get(), 5)
        assert mensaje["type"] == "http.response.body"
        return leer_eventos(mensaje["body"].decode())[0]

    async def desconectar(self):
        await self.entrada.put({"type": "http.disconnect"})
        await asyncio.wait_for(self.tarea, 5)


async def esperar_terminal(client, id_):
    async with asyncio.timeout(5):
        while True:
            estado = (await client.get(f"/generaciones/{id_}")).json()
            if estado["terminal"]:
                return estado
            await asyncio.sleep(0.01)


@pytest.mark.parametrize("desconectar", [False, True])
def test_cancelacion_difiere_confirmacion_hasta_salida_real(entorno, desconectar):
    liberar = Event()
    salio = Event()

    def bloqueante(texto, control):
        control.informar("validando")
        control.informar("generando")
        try:
            assert liberar.wait(5), "La prueba no liberó la operación bloqueante"
        finally:
            salio.set()
        control.comprobar_cancelacion()
        raise AssertionError("No debe avanzar después de la cancelación")

    procesador(bloqueante)

    async def escenario():
        conexion = await ConexionASGI().abrir()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://test"
        ) as client:
            try:
                assert (await conexion.evento())["estado"] == "validando"
                assert (await conexion.evento())["estado"] == "generando"
                assert not salio.is_set()  # Los eventos no se almacenan hasta el final.
                assert (await client.get("/health")).json() == {"status": "ok"}
                if desconectar:
                    await conexion.desconectar()
                    estado = (await client.get(f"/generaciones/{conexion.id}")).json()
                else:
                    respuesta = await client.delete(f"/generaciones/{conexion.id}")
                    assert respuesta.status_code == 202
                    estado = respuesta.json()
                    assert (await client.delete(f"/generaciones/{conexion.id}")).status_code == 202
                assert estado["cancelacion_solicitada"] is True
                assert estado["estado"] == "generando" and not estado["terminal"]
                assert "pipeline_detenido" not in estado and not salio.is_set()
                liberar.set()
                final = await esperar_terminal(client, conexion.id)
                assert salio.is_set()
                assert final["estado"] == "cancelado" and final["pipeline_detenido"] is True
                assert final["cancelacion_remota_confirmada"] is False
                if not desconectar:
                    assert (await conexion.evento())["estado"] == "cancelado"
                    await asyncio.wait_for(conexion.tarea, 5)
                assert (await client.delete(f"/generaciones/{conexion.id}")).status_code == 200
            finally:
                liberar.set()
                if not conexion.tarea.done():
                    await conexion.desconectar()
                await esperar_terminal(client, conexion.id)

    asyncio.run(escenario())


def test_fallo_bloqueante_durante_cancelacion_sigue_siendo_error(entorno):
    liberar = Event()

    def fallar(texto, control):
        control.informar("validando")
        control.informar("generando")
        assert liberar.wait(5)
        raise HTTPException(503, "El modelo no respondió; su ejecución remota es desconocida.")

    procesador(fallar)

    async def escenario():
        conexion = await ConexionASGI().abrir()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://test"
        ) as client:
            try:
                await conexion.evento()
                await conexion.evento()
                await client.delete(f"/generaciones/{conexion.id}")
                liberar.set()
                final = await esperar_terminal(client, conexion.id)
                assert final["estado"] == "error" and final["cancelacion_solicitada"]
                assert "pipeline_detenido" not in final
                assert (await conexion.evento())["estado"] == "error"
                await asyncio.wait_for(conexion.tarea, 5)
            finally:
                liberar.set()
                if not conexion.tarea.done():
                    await conexion.desconectar()
                await esperar_terminal(client, conexion.id)

    asyncio.run(escenario())


def test_cancelar_antes_de_ejecutar_no_invoca_procesador():
    trabajo = Trabajo()
    trabajo.cancelar()

    def no_ejecutar(*args):
        raise AssertionError("Se ejecutó un trabajo cancelado antes de empezar")

    terminales = []
    trabajo.ejecutar("Pieza", no_ejecutar, terminales.append)
    assert trabajo.estado()["estado"] == "cancelado"
    assert len(terminales) == 1


def test_retencion_no_expulsa_trabajos_activos():
    gestor = GestorTrabajos(capacidad=1)
    liberar = Event()
    fin = Event()

    def generar(texto, control):
        control.informar("validando")
        control.informar("generando")
        assert liberar.wait(5)
        return {"step": "pieza.step"}

    trabajo = gestor.crear("Pieza", generar, lambda _: fin.set())
    try:
        with pytest.raises(HTTPException) as error:
            gestor.crear("Pieza", generar, lambda _: None)
        assert error.value.status_code == 503
        assert gestor.obtener(trabajo.id) is trabajo
    finally:
        liberar.set()
        assert fin.wait(5)


@pytest.mark.parametrize("fallar_en", ["http.response.start", "http.response.body"])
def test_desconexion_asgi_24_solicita_cancelacion_incluso_al_enviar(fallar_en):
    async def escenario():
        trabajo = Trabajo()
        trabajo.control.informar("validando")
        scope = {"type": "http", "asgi": {"spec_version": "2.4"}}

        async def recibir():
            await asyncio.Future()

        async def enviar(mensaje):
            if mensaje["type"] == fallar_en:
                raise OSError("Conexión cerrada")

        respuesta = RespuestaSSE(trabajo, Request(scope, recibir))
        try:
            with pytest.raises(ClientDisconnect):
                await respuesta(scope, recibir, enviar)
            estado = trabajo.estado()
            assert estado["cancelacion_solicitada"] and not estado["terminal"]
            assert "pipeline_detenido" not in estado
        finally:
            await respuesta.body_iterator.aclose()

    asyncio.run(escenario())


@pytest.mark.parametrize("resultado", ["verificado", "declinado", "error"])
def test_sse_integra_pipeline_real_sin_servicios(entorno, monkeypatch, tmp_path, resultado):
    pytest.importorskip("cadquery")
    from m2_cad import pipeline

    generar_real = pipeline.generar_pieza

    def planificar(texto):
        if resultado == "declinado":
            return {"unsupported": "engranaje helicoidal"}
        if resultado == "error":
            raise pipeline.ModeloNoDisponible("Fallo en http://10.0.0.5:8080; api_key=privada")
        return {
            "parts": [{"id": "p", "type": "spacer", "material": "steel", "params": {}}],
            "mates": [],
        }

    def generar(texto, *, control):
        return generar_real(
            texto,
            control=control,
            planificar=planificar,
            directorio=tmp_path,
        )

    monkeypatch.setenv("LLM_BASE_URL", "http://modelo-no-consultado")
    monkeypatch.setattr(pipeline, "generar_pieza", generar)
    with TestClient(api.app) as client:
        respuesta = client.post(
            "/generar", json={"texto": "Espaciador"}, headers={"Accept": "text/event-stream"}
        )
    eventos = leer_eventos(respuesta.text)
    assert [e["estado"] for e in eventos] == ["validando", "generando", resultado]
    assert sum(e["terminal"] for e in eventos) == 1
    if resultado == "verificado":
        assert eventos[-1]["resultado"]["aviso"] == pipeline.MARCA_PRELIMINAR
    else:
        assert "resultado" not in eventos[-1]
    assert "10.0.0.5" not in respuesta.text and "api_key" not in respuesta.text


def test_archivos_reales_independientes_y_head(entorno, tmp_path):
    salidas = tmp_path / "outputs"
    salidas.mkdir()
    step = salidas / "pieza.step"
    csv = salidas / "materiales.csv"
    step.write_bytes(b"ISO-10303-21;\nSTEP de prueba")
    csv.write_bytes(b"material,cantidad\nacero,1\n")

    def generar(texto, control):
        control.informar("validando")
        control.informar("generando")
        return {"step": str(step), "glb": str(salidas / "ausente.glb"), "bom_csv": str(csv)}

    procesador(generar)
    api.app.dependency_overrides[api.obtener_directorio_salidas] = lambda: salidas
    try:
        with TestClient(api.app) as client:
            response = client.post(
                "/generar", json={"texto": "Placa"}, headers={"Accept": "text/event-stream"}
            )
            id_ = response.headers["x-solicitud-id"]
            base = f"/generaciones/{id_}/archivos"
            assert client.get(f"{base}/step").content == step.read_bytes()
            assert client.get(f"{base}/csv").content == csv.read_bytes()
            head = client.head(f"{base}/step")
            assert head.status_code == 200 and head.content == b""
            assert "pieza.step" in head.headers["content-disposition"]
            assert client.head(f"{base}/glb").status_code == 404
            assert client.get(f"{base}/desconocido").status_code == 404
    finally:
        api.app.dependency_overrides.pop(api.obtener_directorio_salidas, None)


@pytest.mark.parametrize("nombre", ["../privado.step", "absoluto", "invalido.txt", "", None, 123])
def test_descargas_no_exponen_archivos_ajenos_o_extension_incorrecta(entorno, tmp_path, nombre):
    salidas = tmp_path / "outputs"
    salidas.mkdir()
    (tmp_path / "privado.step").write_bytes(b"privado")
    (salidas / "invalido.txt").write_bytes(b"extension incorrecta")
    if nombre == "absoluto":
        nombre = str(tmp_path / "privado.step")

    def generar(texto, control):
        control.informar("validando")
        control.informar("generando")
        return {"step": nombre}

    procesador(generar)
    api.app.dependency_overrides[api.obtener_directorio_salidas] = lambda: salidas
    try:
        with TestClient(api.app) as client:
            response = client.post(
                "/generar", json={"texto": "Placa"}, headers={"Accept": "text/event-stream"}
            )
            id_ = response.headers["x-solicitud-id"]
            assert client.get(f"/generaciones/{id_}/archivos/step").status_code == 404
    finally:
        api.app.dependency_overrides.pop(api.obtener_directorio_salidas, None)


@pytest.mark.parametrize("prefijo", ["outputs/", ""])
def test_descarga_resuelve_rutas_relativas_con_raiz_real(entorno, tmp_path, monkeypatch, prefijo):
    monkeypatch.chdir(tmp_path)
    salidas = tmp_path / "outputs" / "trabajo"
    salidas.mkdir(parents=True)
    (salidas / "pieza.step").write_bytes(b"STEP real de prueba")

    def generar(texto, control):
        control.informar("validando")
        control.informar("generando")
        return {"step": f"{prefijo}trabajo/pieza.step"}

    procesador(generar)
    with TestClient(api.app) as client:
        response = client.post(
            "/generar", json={"texto": "Placa"}, headers={"Accept": "text/event-stream"}
        )
        id_ = response.headers["x-solicitud-id"]
        archivo = client.get(f"/generaciones/{id_}/archivos/step")
        assert archivo.status_code == 200 and archivo.content == b"STEP real de prueba"
