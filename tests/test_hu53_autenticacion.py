"""HU-53: acceso anónimo, aislamiento entre usuarios y trazabilidad (SPEC-054)."""

import csv
import json
import secrets
import sys
import uuid
from contextlib import suppress
from threading import Thread
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from m2_cad import api, autenticacion, registro, seguimiento
from m2_cad.autenticacion import (
    COOKIE_NOMBRE,
    LimiteIntentos,
    emitir_sesion,
    hash_clave,
    usuarios,
    validar_sesion,
    verificar_clave,
    verificar_usuario,
)
from m2_cad.cola_trabajos import ColaTrabajos
from m2_cad.control_uso import ConfiguracionUso, ControlUso
from m2_cad.registro import CAMPOS, registrar
from m2_cad.trabajos import GestorTrabajos
from m2_cad.worker import consumir


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Autenticación activa, dos usuarios y dependencias aisladas del hardware."""
    gestor = GestorTrabajos()
    claves = {"ana": "clave-ana-53", "bob": "clave-bob-53"}
    hashes = {usuario: hash_clave(clave) for usuario, clave in claves.items()}
    monkeypatch.setenv("M2_AUTH_ENABLED", "1")
    monkeypatch.setenv("M2_AUTH_SECRET", secrets.token_hex(32))
    monkeypatch.setenv("M2_AUTH_USERS", json.dumps(hashes))
    monkeypatch.setenv("M2_AUTH_COOKIE_SECURE", "0")
    monkeypatch.setenv("M2_AUTH_TTL_SECONDS", "3600")
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", secrets.token_hex(32))
    ruta_registro = tmp_path / "registro.csv"
    monkeypatch.setattr(api, "RUTA_DEFAULT", ruta_registro)
    previo = dict(api.app.dependency_overrides)
    api.app.dependency_overrides[api.obtener_gestor_trabajos] = lambda: gestor
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: (
        seguimiento.Configuracion(activo=False)
    )
    # Límite de intentos propio de cada prueba: los fallos de una no afectan a otra.
    limite = LimiteIntentos()
    api.app.dependency_overrides[api.obtener_limite_login] = lambda: limite
    try:
        yield SimpleNamespace(
            gestor=gestor,
            claves=claves,
            ruta_registro=ruta_registro,
            tmp_path=tmp_path,
        )
    finally:
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(previo)


def entrar(usuario: str, clave: str) -> TestClient:
    cliente = TestClient(api.app)
    respuesta = cliente.post("/v1/auth/login", json={"usuario": usuario, "clave": clave})
    assert respuesta.status_code == 200
    return cliente


def generar_sse(cliente: TestClient, archivo) -> tuple[str, str]:
    def procesar(texto, control, medicion=None):
        control.informar("validando")
        control.informar("generando")
        return {"step": str(archivo)}

    api.app.dependency_overrides[api.obtener_procesador_sse] = lambda: procesar
    respuesta = cliente.post(
        "/v1/generar",
        json={"texto": "Espaciador de 14 mm"},
        headers={"Accept": "text/event-stream"},
    )
    assert respuesta.status_code == 200
    return respuesta.headers["x-registro-id"], respuesta.headers["x-download-token"]


def filas_csv(ruta) -> list[dict[str, str]]:
    with ruta.open(newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def test_ac1_ac4_anónimo_no_genera_y_salud_queda_abierta(entorno):
    with TestClient(api.app) as cliente:
        assert cliente.get("/v1/health").status_code == 200
        assert cliente.get("/v1/ready").status_code != 401  # salud abierta, sin sesión
        assert cliente.get("/v1/auth/me").json() == {
            "requerido": True,
            "autenticado": False,
            "usuario": None,
        }
        identificador = uuid.uuid4().hex
        assert cliente.post("/v1/generar", json={"texto": "Placa"}).status_code == 401
        assert cliente.get(f"/v1/generaciones/{identificador}").status_code == 401
        assert cliente.delete(f"/v1/generaciones/{identificador}").status_code == 401
        assert cliente.get(f"/v1/registros/{identificador}").status_code == 401

    assert not entorno.ruta_registro.exists()
    assert not entorno.gestor._trabajos


def test_ac2_aislamiento_de_trabajos_registro_y_descargas(entorno):
    salidas = entorno.tmp_path / "outputs"
    salidas.mkdir()
    archivo = salidas / "pieza.step"
    archivo.write_text("STEP_DE_ANA", encoding="utf-8")
    api.app.dependency_overrides[api.obtener_directorio_salidas] = lambda: salidas
    with entrar("ana", entorno.claves["ana"]) as ana:
        identificador, token = generar_sse(ana, archivo)
        with entrar("bob", entorno.claves["bob"]) as bob:
            assert ana.get(f"/v1/generaciones/{identificador}").status_code == 200
            assert bob.get(f"/v1/generaciones/{identificador}").status_code == 404
            assert bob.delete(f"/v1/generaciones/{identificador}").status_code == 404
            assert bob.get(f"/v1/registros/{identificador}").status_code == 404
            assert (
                bob.get(
                    f"/v1/generaciones/{identificador}/archivos/step",
                    headers={"X-Download-Token": token},
                ).status_code
                == 404
            )
            assert (
                bob.get(
                    f"/v1/registros/{identificador}/step", headers={"X-Download-Token": token}
                ).status_code
                == 404
            )
            descarga = ana.get(
                f"/v1/generaciones/{identificador}/archivos/step",
                headers={"X-Download-Token": token},
            )
            assert descarga.status_code == 200
            assert descarga.content == b"STEP_DE_ANA"
            assert ana.get(f"/v1/registros/{identificador}").json()["usuario"] == "ana"

    fila = filas_csv(entorno.ruta_registro)
    assert len(fila) == 1
    assert fila[0]["id"] == identificador
    assert fila[0]["usuario"] == "ana"
    assert "clave-ana-53" not in json.dumps(fila, ensure_ascii=False)


def test_login_invalido_cookie_firmada_y_logout(entorno):
    with TestClient(api.app) as cliente:
        assert (
            cliente.post(
                "/v1/auth/login", json={"usuario": "ana", "clave": "incorrecta"}
            ).status_code
            == 401
        )
        assert (
            cliente.post("/v1/auth/login", json={"usuario": "nadie", "clave": "x"}).status_code
            == 401
        )
        respuesta = cliente.post(
            "/v1/auth/login", json={"usuario": "ana", "clave": entorno.claves["ana"]}
        )
        assert respuesta.status_code == 200
        assert respuesta.json() == {"autenticado": True, "usuario": "ana"}
        cookie = respuesta.headers["set-cookie"]
        assert COOKIE_NOMBRE in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie
        assert "Secure" not in cookie
        assert cliente.get("/v1/auth/me").json()["usuario"] == "ana"
        assert cliente.post("/v1/auth/logout").json() == {"autenticado": False}
        assert cliente.get("/v1/auth/me").json()["autenticado"] is False


def test_cookie_manipulada_o_expirada_no_autentica(entorno):
    token = emitir_sesion("ana", ahora=1_000)
    assert validar_sesion(token, ahora=1_500) == "ana"
    assert validar_sesion(token, ahora=1_000 + 3_600) is None
    firma = token.rsplit(".", 1)[1]
    manipulada = token.rsplit(".", 1)[0] + "." + ("0" if firma[0] != "0" else "1") + firma[1:]
    assert validar_sesion(manipulada, ahora=1_500) is None
    assert validar_sesion("v1.basura.2000000000." + "0" * 64, ahora=1_500) is None

    with TestClient(api.app) as cliente:
        cliente.cookies.set(COOKIE_NOMBRE, manipulada)
        assert cliente.get("/v1/auth/me").json()["autenticado"] is False
        assert cliente.post("/v1/generar", json={"texto": "Placa"}).status_code == 401


def test_hash_pbkdf2_y_cli(monkeypatch, capsys):
    guardado = hash_clave("clave-secreta")
    assert guardado.startswith("pbkdf2_sha256$")
    assert verificar_clave("clave-secreta", guardado)
    assert not verificar_clave("otra", guardado)
    assert not verificar_clave("clave-secreta", "basura")

    from m2_cad.usuarios import main

    monkeypatch.setenv("M2_CLAVE_NUEVA", "clave-cli")
    monkeypatch.setattr(sys, "argv", ["usuarios", "hash"])
    assert main() == 0
    hash_cli = capsys.readouterr().out.strip()
    assert verificar_clave("clave-cli", hash_cli)


def test_modo_local_explícito_sigue_anónimo(entorno, monkeypatch):
    monkeypatch.setenv("M2_AUTH_ENABLED", "0")

    def procesar(texto, medicion=None):
        return {"resultado": "pieza"}

    api.app.dependency_overrides[api.obtener_procesador] = lambda: procesar
    with TestClient(api.app) as cliente:
        assert cliente.get("/v1/auth/me").json()["requerido"] is False
        respuesta = cliente.post("/v1/generar", json={"texto": "Placa"})
        assert respuesta.status_code == 200
        assert cliente.get(respuesta.headers["x-registro-url"]).json()["usuario"] == "anónimo"
    api.app.dependency_overrides.pop(api.obtener_procesador, None)


@pytest.mark.parametrize(
    ("valor", "patron"),
    [("abc", "entero"), ("1", "entre"), ("9999999", "entre")],
)
def test_configuracion_ttl_invalida(monkeypatch, valor, patron):
    monkeypatch.setenv("M2_AUTH_SECRET", secrets.token_hex(32))
    monkeypatch.setenv("M2_AUTH_TTL_SECONDS", valor)
    with pytest.raises(RuntimeError, match=patron):
        emitir_sesion("ana", ahora=1)


def test_configuracion_usuarios_invalida(monkeypatch):
    monkeypatch.setenv("M2_AUTH_SECRET", secrets.token_hex(32))
    for valor, patron in [
        ("", "M2_AUTH_USERS"),
        ("{", "JSON"),
        ("{}", "al menos"),
        ('{"ana!": "x"}', "inválido"),
    ]:
        monkeypatch.setenv("M2_AUTH_USERS", valor)
        with pytest.raises(RuntimeError, match=patron):
            usuarios()


def test_usuario_invalido_y_login_desactivado(entorno, monkeypatch):
    assert verificar_usuario("ana!", entorno.claves["ana"]) is False
    monkeypatch.setenv("M2_AUTH_ENABLED", "0")
    with TestClient(api.app) as cliente:
        assert (
            cliente.post(
                "/v1/auth/login", json={"usuario": "ana", "clave": entorno.claves["ana"]}
            ).status_code
            == 404
        )


def test_csv_anterior_se_migra_sin_perder_filas(tmp_path):
    ruta = tmp_path / "registro.csv"
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS[:-1])
        escritor.writeheader()
        escritor.writerow({campo: "valor" for campo in CAMPOS[:-1]} | {"id": "anterior"})

    registrar(
        texto="Placa",
        traduccion="no aplica",
        resultado={},
        latencia_ms=1,
        ruta=ruta,
        identificador="nuevo",
        usuario="ana",
    )
    filas = filas_csv(ruta)
    assert [fila["id"] for fila in filas] == ["anterior", "nuevo"]
    assert filas[0]["usuario"] == "anónimo"
    assert filas[1]["usuario"] == "ana"


# --- Integración con HU-31 (/v1), HU-32 (uso) y HU-45 (cola) ---------------------


@pytest.fixture
def cola_con_worker(entorno, monkeypatch):
    """Cola activa como en el despliegue y un worker real en un hilo (HU-45)."""
    ruta = entorno.tmp_path / "cola.json"
    salidas = entorno.tmp_path / "outputs"
    salidas.mkdir()
    monkeypatch.setenv("M2_COLA_HABILITADA", "1")
    cola = ColaTrabajos(ruta, propietario="api-prueba")
    monkeypatch.setattr(api, "cola_trabajos", cola)
    api.app.dependency_overrides[api.obtener_cola_trabajos] = lambda: cola
    api.app.dependency_overrides[api.obtener_directorio_salidas] = lambda: salidas
    tags: list[dict] = []
    iniciar = seguimiento.iniciar_corrida

    def iniciar_y_capturar(*args, **kwargs):
        tags.append(kwargs.get("tags") or {})
        return iniciar(*args, **kwargs)

    monkeypatch.setattr(seguimiento, "iniciar_corrida", iniciar_y_capturar)

    def procesar(texto, control, medido=None):
        control.informar("validando")
        control.informar("generando")
        archivo = salidas / f"{uuid.uuid4().hex}.step"
        archivo.write_text("STEP_DE_LA_COLA", encoding="utf-8")
        return {"step": str(archivo)}

    worker = Thread(target=consumir, args=(cola, procesar), kwargs={"intervalo": 0.01}, daemon=True)
    worker.start()
    yield SimpleNamespace(cola=cola, tags=tags)
    cola.cerrar()
    worker.join(timeout=5)


def test_cola_aisla_por_usuario_registra_al_dueno_y_entrega_descargas(entorno, cola_con_worker):
    """S2/S3/S9: con la cola activa, otro usuario recibe 404 y el dueño descarga."""
    # Arrange
    sse = {"Accept": "text/event-stream"}

    # Act
    with entrar("ana", entorno.claves["ana"]) as ana, entrar("bob", entorno.claves["bob"]) as bob:
        respuesta = ana.post("/v1/generar", json={"texto": "Espaciador"}, headers=sse)
        identificador = respuesta.headers["x-registro-id"]
        token = {"X-Download-Token": respuesta.headers["x-download-token"]}
        archivo = f"/v1/generaciones/{identificador}/archivos/step"
        ajenas = [
            bob.get(f"/v1/generaciones/{identificador}").status_code,
            bob.delete(f"/v1/generaciones/{identificador}").status_code,
            bob.get(archivo, headers=token).status_code,
            bob.get(f"/v1/registros/{identificador}").status_code,
        ]
        estado = ana.get(f"/v1/generaciones/{identificador}").json()
        descarga = ana.get(archivo, headers=token)
        registro_ana = ana.get(f"/v1/registros/{identificador}").json()
        cancelacion_propia = ana.delete(f"/v1/generaciones/{identificador}")

    # Assert
    assert respuesta.status_code == 200
    assert ajenas == [404, 404, 404, 404]
    assert estado["estado"] == "verificado"
    assert estado["cancelacion_solicitada"] is False
    assert descarga.status_code == 200 and descarga.content == b"STEP_DE_LA_COLA"
    assert registro_ana["usuario"] == "ana"
    assert cancelacion_propia.status_code == 200  # terminal: confirma sin cancelar
    assert cancelacion_propia.json()["estado"] == "verificado"
    assert [fila["usuario"] for fila in filas_csv(entorno.ruta_registro)] == ["ana"]
    assert [tag.get("usuario") for tag in cola_con_worker.tags] == ["ana"]


def test_idempotencia_y_topes_pertenecen_al_usuario(entorno):
    """S4: misma clave, texto, IP y X-Session-ID no cruzan generaciones entre usuarios."""
    # Arrange
    llamadas: list[str] = []

    def procesar(texto, medicion=None):
        llamadas.append(texto)
        return {"resultado": "entregada"}

    control = ControlUso(ConfiguracionUso(limite_ventana=1, ventana_segundos=60))
    api.app.dependency_overrides[api.obtener_procesador] = lambda: procesar
    api.app.dependency_overrides[api.obtener_control_uso] = lambda: control
    comunes = {"Idempotency-Key": "pedido-1", "X-Session-ID": "oficina"}
    cuerpo = {"texto": "Placa base"}

    # Act
    with entrar("ana", entorno.claves["ana"]) as ana, entrar("bob", entorno.claves["bob"]) as bob:
        original = ana.post("/v1/generar", json=cuerpo, headers=comunes)
        de_bob = bob.post("/v1/generar", json=cuerpo, headers=comunes)
        repetida = ana.post("/v1/generar", json=cuerpo, headers=comunes)
        sobre_tope = ana.post("/v1/generar", json=cuerpo, headers={"X-Session-ID": "oficina"})

    # Assert
    assert original.status_code == 200 and de_bob.status_code == 200
    assert "Idempotent-Replay" not in de_bob.headers
    assert de_bob.headers["X-Registro-ID"] != original.headers["X-Registro-ID"]
    assert repetida.headers["Idempotent-Replay"] == "true"
    assert repetida.headers["X-Registro-ID"] == original.headers["X-Registro-ID"]
    assert sobre_tope.status_code == 429
    assert llamadas == ["Placa base", "Placa base"]


def test_entrada_invalida_registra_al_usuario_autenticado(entorno):
    """S6: el 422 de una sesión válida conserva su usuario; sin sesión es 401."""
    # Act
    with entrar("ana", entorno.claves["ana"]) as ana:
        invalida = ana.post("/v1/generar", json={"texto": "   "})
    with TestClient(api.app) as anonimo:
        sin_sesion = anonimo.post("/v1/generar", json={"texto": "   "})

    # Assert
    assert invalida.status_code == 422
    assert sin_sesion.status_code == 401
    assert [fila["usuario"] for fila in filas_csv(entorno.ruta_registro)] == ["ana"]


def test_auth_se_publica_solo_bajo_v1(entorno):
    """S5: las rutas de sesión forman parte del contrato /v1."""
    # Act
    rutas = api.app.openapi()["paths"]
    with TestClient(api.app) as cliente:
        plana = cliente.get("/auth/me")
        uso = cliente.get("/v1/uso")

    # Assert
    assert {"/v1/auth/login", "/v1/auth/logout", "/v1/auth/me"} <= rutas.keys()
    assert not any(ruta.startswith("/auth") for ruta in rutas)
    assert plana.status_code == 404
    assert uso.status_code == 401


def test_login_limita_intentos_fallidos(entorno):
    """S7: tras agotar los intentos, ni la clave correcta entra hasta que pasa la ventana."""
    # Arrange
    ahora = [0.0]
    limite = LimiteIntentos(reloj=lambda: ahora[0])
    api.app.dependency_overrides[api.obtener_limite_login] = lambda: limite
    correcta = {"usuario": "ana", "clave": entorno.claves["ana"]}

    # Act
    with TestClient(api.app) as cliente:
        fallidos = [
            cliente.post("/v1/auth/login", json={"usuario": "ana", "clave": "mala"}).status_code
            for _ in range(5)
        ]
        bloqueado = cliente.post("/v1/auth/login", json=correcta)
        ahora[0] = 301.0
        tras_ventana = cliente.post("/v1/auth/login", json=correcta)

    # Assert
    assert fallidos == [401] * 5
    assert bloqueado.status_code == 429
    assert int(bloqueado.headers["Retry-After"]) >= 1
    assert COOKIE_NOMBRE not in bloqueado.cookies
    assert tras_ventana.status_code == 200


def test_sesion_se_revoca_al_quitar_usuario_o_cambiar_clave(entorno, monkeypatch):
    """S7: la firma depende del hash vigente; el token anterior deja de valer."""
    # Arrange
    token = emitir_sesion("ana", ahora=1_000)
    originales = usuarios()

    # Act
    vigente = validar_sesion(token, ahora=1_500)
    monkeypatch.setenv("M2_AUTH_USERS", json.dumps({**originales, "ana": hash_clave("nueva")}))
    tras_cambio = validar_sesion(token, ahora=1_500)
    monkeypatch.setenv("M2_AUTH_USERS", json.dumps({"bob": originales["bob"]}))
    tras_baja = validar_sesion(token, ahora=1_500)

    # Assert
    assert vigente == "ana"
    assert tras_cambio is None
    assert tras_baja is None


def test_usuario_inexistente_tambien_deriva_pbkdf2(entorno, monkeypatch):
    """S7: el costo no revela qué usuarios existen."""
    # Arrange
    derivaciones: list[str] = []
    real = autenticacion.verificar_clave

    def contar(clave, guardado):
        derivaciones.append(guardado)
        return real(clave, guardado)

    monkeypatch.setattr(autenticacion, "verificar_clave", contar)

    # Act
    resultado = verificar_usuario("nadie", "x")

    # Assert
    assert resultado is False
    assert len(derivaciones) == 1
    assert derivaciones[0].startswith("pbkdf2_sha256$")


def test_configuracion_invalida_impide_arrancar(entorno, monkeypatch):
    """S7: sin secreto la API no arranca, en vez de responder 500 al iniciar sesión."""
    # Arrange
    monkeypatch.delenv("M2_AUTH_SECRET")

    # Act / Assert
    with pytest.raises(RuntimeError, match="M2_AUTH_SECRET"):
        with TestClient(api.app):
            pass


def test_migracion_del_registro_se_comprueba_una_vez_por_archivo(tmp_path, monkeypatch):
    """S8: la cabecera no se relee en cada escritura."""
    # Arrange
    llamadas: list = []
    real = registro._asegurar_columna_usuario
    monkeypatch.setattr(
        registro, "_asegurar_columna_usuario", lambda ruta: (llamadas.append(ruta), real(ruta))
    )
    ruta = tmp_path / "registro.csv"

    # Act
    for _ in range(3):
        registrar("Placa", "no aplica", None, 1.0, None, "v", ruta)

    # Assert
    assert len(llamadas) == 1
    assert len(filas_csv(ruta)) == 3


def test_login_concurrente_no_supera_el_limite(entorno):
    """H1: los intentos simultáneos se anotan bajo un lock; no pasan todos el control."""
    # Arrange
    import threading

    limite = LimiteIntentos()
    barrera = threading.Barrier(30)
    admitidos: list[int] = []

    def intentar():
        barrera.wait()
        try:
            limite.intentar("10.0.0.1", "ana")
            admitidos.append(1)
        except Exception:
            pass

    hilos = [threading.Thread(target=intentar) for _ in range(30)]

    # Act
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    # Assert
    assert len(admitidos) == 5


def test_login_exitoso_de_otra_cuenta_no_borra_los_fallos(entorno):
    """H2: entrar con la propia cuenta no reinicia la fuerza bruta contra otra."""
    # Arrange
    contra_ana = {"usuario": "ana", "clave": "mala"}

    # Act
    with TestClient(api.app) as cliente:
        primeros = [cliente.post("/v1/auth/login", json=contra_ana).status_code for _ in range(4)]
        de_bob = cliente.post(
            "/v1/auth/login", json={"usuario": "bob", "clave": entorno.claves["bob"]}
        )
        quinto = cliente.post("/v1/auth/login", json=contra_ana)
        correcta = cliente.post(
            "/v1/auth/login", json={"usuario": "ana", "clave": entorno.claves["ana"]}
        )

    # Assert
    assert primeros == [401] * 4
    assert de_bob.status_code == 200
    assert quinto.status_code == 401
    assert correcta.status_code == 429


def test_anonimo_con_json_mal_formado_no_escribe_en_el_registro(entorno):
    """H3: sin sesión, un cuerpo inválido es 401 y no crea filas."""
    # Act
    with TestClient(api.app) as cliente:
        respuesta = cliente.post(
            "/v1/generar", content=b"{no json", headers={"Content-Type": "application/json"}
        )

    # Assert
    assert respuesta.status_code == 401
    assert not entorno.ruta_registro.exists()


def test_recurso_ajeno_responde_igual_que_uno_inexistente(entorno):
    """H5: el 404 no distingue «de otro usuario» de «no existe»."""
    # Arrange
    salidas = entorno.tmp_path / "outputs"
    salidas.mkdir()
    archivo = salidas / "pieza.step"
    archivo.write_text("STEP", encoding="utf-8")

    # Act
    with entrar("ana", entorno.claves["ana"]) as ana:
        identificador, _ = generar_sse(ana, archivo)
        with entrar("bob", entorno.claves["bob"]) as bob:
            otro = uuid.uuid4().hex
            pares = [
                (bob.get(f"/v1/generaciones/{identificador}"), bob.get(f"/v1/generaciones/{otro}")),
                (bob.get(f"/v1/registros/{identificador}"), bob.get(f"/v1/registros/{otro}")),
            ]

    # Assert
    for ajeno, inexistente in pares:
        assert ajeno.status_code == inexistente.status_code == 404
        assert ajeno.json() == inexistente.json()


def test_hash_sin_iteraciones_es_configuracion_invalida(entorno, monkeypatch):
    """H6: un hash con 0 iteraciones se rechaza al validar, no con un 500 al entrar."""
    # Arrange
    guardado = usuarios()["ana"].split("$")
    guardado[1] = "0"
    monkeypatch.setenv("M2_AUTH_USERS", json.dumps({"ana": "$".join(guardado)}))

    # Act / Assert
    with pytest.raises(RuntimeError, match="hash inválido"):
        autenticacion.validar_configuracion()


def test_limite_por_cliente_sobrevive_a_un_acierto(entorno, monkeypatch):
    """H2: el contador por cliente (4 × máximo) no se borra al entrar con otra cuenta."""
    # Arrange
    monkeypatch.setenv("M2_AUTH_MAX_INTENTOS", "1")
    limite = LimiteIntentos()

    # Act
    limite.intentar("10.0.0.1", "ana")  # fallo: no se retira
    limite.acertar(limite.intentar("10.0.0.1", "bob"))
    for usuario in ("carla", "dario", "eva"):
        limite.intentar("10.0.0.1", usuario)

    # Assert
    with pytest.raises(autenticacion.IntentosAgotados):
        limite.intentar("10.0.0.1", "fabio")


def test_limite_de_login_no_acumula_claves_sin_limite(entorno, monkeypatch):
    """R1/R4: claves vencidas se eliminan, el total está acotado y un cliente agotado
    no crea claves nuevas por usuario."""
    # Arrange
    ahora = [0.0]
    limite = LimiteIntentos(reloj=lambda: ahora[0])
    monkeypatch.setattr(autenticacion, "MAX_CLAVES_LIMITE", 50)

    # Act: un cliente agota su contador y sigue probando usuarios distintos.
    for indice in range(200):
        with suppress(autenticacion.IntentosAgotados):
            limite.intentar("10.0.0.1", f"u{indice}")
    tras_agotar = len(limite._fallos)
    for indice in range(500):  # muchos clientes distintos
        with suppress(autenticacion.IntentosAgotados):
            limite.intentar(f"10.1.{indice // 250}.{indice % 250}", "ana")
    acotado = len(limite._fallos)
    ahora[0] = 10_000.0  # todo venció
    limite.acertar(limite.intentar("10.9.9.9", "ana"))
    tras_vencer = len(limite._fallos)

    # Assert
    assert tras_agotar == 1 + 20  # clave del cliente + 20 pares admitidos (4 × 5)
    assert acotado <= 50
    assert tras_vencer == 0


def test_usuario_invalido_comparte_una_sola_clave_del_limite(entorno):
    """R1: nombres arbitrarios (inválidos) no crean una clave por nombre."""
    # Arrange
    limite = LimiteIntentos()

    # Act
    for nombre in ("<a>", "con espacio", "x" * 64 + "!"):
        limite.intentar("10.0.0.2", nombre)

    # Assert
    assert sorted(limite._fallos) == ["cliente:10.0.0.2", "par:10.0.0.2\n-"]
