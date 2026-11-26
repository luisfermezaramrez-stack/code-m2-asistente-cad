"""HU-10 AC3/AC4: prueba de humo y latencia del despliegue; sin red ni modelo real."""

import csv
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

RUTA = Path(__file__).resolve().parents[1] / "scripts" / "smoke_deploy.py"
especificacion = importlib.util.spec_from_file_location("smoke_deploy", RUTA)
smoke = importlib.util.module_from_spec(especificacion)
especificacion.loader.exec_module(smoke)


def _transporte(fallar_en: str | None = None):
    """Simula /generar: pieza para los positivos, declinación para los negativos."""

    negativos = {f["solicitud"] for f in smoke.read_dataset() if f["familia"] == "fuera_alcance"}

    def responder(request: httpx.Request) -> httpx.Response:
        if request.url.path != "/v1/generar":
            return httpx.Response(404)
        texto = json.loads(request.content)["texto"]
        if fallar_en and fallar_en == texto:
            return httpx.Response(503, json={"detail": "El modelo no está disponible."})
        if texto in negativos:
            return httpx.Response(422, json={"detail": "Pieza declinada: fuera del catálogo"})
        return httpx.Response(200, json={"step": "/salidas/pieza.step"})

    return httpx.MockTransport(responder)


def test_seleccion_alterna_familias_para_la_prueba_de_humo():
    # Arrange
    filas = smoke.read_dataset()

    # Act
    elegidas = smoke.seleccionar(filas, 5)

    # Assert
    assert [fila["familia"] for fila in elegidas] == [
        "plate",
        "sheet_bracket",
        "adapter",
        "flange",
        "spacer",
    ]


def test_seleccion_por_ids_respeta_el_orden_pedido():
    filas = smoke.read_dataset()

    elegidas = smoke.seleccionar(filas, 5, ids=["HU02-N01", "HU02-P02"])

    assert [fila["id"] for fila in elegidas] == ["HU02-N01", "HU02-P02"]


def test_seleccion_rechaza_id_inexistente():
    with pytest.raises(ValueError, match="HU02-X99"):
        smoke.seleccionar(smoke.read_dataset(), 5, ids=["HU02-X99"])


@pytest.mark.parametrize(
    ("valores", "p50", "p90"),
    [([1.0], 1.0, 1.0), ([3.0, 1.0, 2.0, 4.0], 2.0, 4.0), (list(range(1, 11)), 5, 9)],
)
def test_percentiles_por_rango_mas_cercano(valores, p50, p90):
    assert smoke.percentil(valores, 50) == p50
    assert smoke.percentil(valores, 90) == p90


def test_humo_exitoso_escribe_csv_y_resumen(tmp_path, capsys):
    # Arrange
    argv = ["--n", "7", "--salida", str(tmp_path)]

    # Act
    codigo = smoke.main(argv, transport=_transporte())

    # Assert
    assert codigo == 0
    with (tmp_path / "smoke.csv").open(encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    assert [fila["familia"] for fila in filas][-1] == "fuera_alcance"
    assert {fila["resultado"] for fila in filas} == {"pieza", "declinada"}
    assert all(float(fila["latencia_s"]) >= 0 for fila in filas)
    resumen = json.loads((tmp_path / "smoke.json").read_text(encoding="utf-8"))
    assert resumen["n"] == 7 and resumen["validas"] == 7
    assert resumen["p50_s"] <= resumen["p90_s"]
    assert "7/7" in capsys.readouterr().out


def test_humo_con_un_fallo_devuelve_codigo_1(tmp_path):
    fila = smoke.seleccionar(smoke.read_dataset(), 2)[1]

    codigo = smoke.main(
        ["--n", "2", "--salida", str(tmp_path)], transport=_transporte(fila["solicitud"])
    )

    assert codigo == 1
    resumen = json.loads((tmp_path / "smoke.json").read_text(encoding="utf-8"))
    assert resumen["validas"] == 1
    with (tmp_path / "smoke.csv").open(encoding="utf-8") as archivo:
        fallida = list(csv.DictReader(archivo))[1]
    assert fallida["estado_http"] == "503" and fallida["resultado"] == "error"


def test_un_422_de_validacion_no_cuenta_como_declinacion(tmp_path):
    transporte = httpx.MockTransport(
        lambda request: httpx.Response(422, json={"detail": [{"msg": "texto vacío"}]})
    )

    codigo = smoke.main(["--n", "1", "--salida", str(tmp_path)], transport=transporte)

    assert codigo == 1


def _transporte_con_sesion(llamadas: list[httpx.Request]):
    """API con HU-53 activa: exige la cookie de sesión en /v1/generar."""

    def responder(request: httpx.Request) -> httpx.Response:
        llamadas.append(request)
        if request.url.path == "/v1/auth/me":
            return httpx.Response(200, json={"requerido": True, "autenticado": False})
        if request.url.path == "/v1/auth/login":
            datos = json.loads(request.content)
            if datos != {"usuario": "operador", "clave": "clave-humo"}:
                return httpx.Response(401, json={"detail": "Usuario o clave incorrectos."})
            # Cookie Secure como en producción: httpx no la reenviaría por HTTP.
            return httpx.Response(
                200,
                json={"autenticado": True, "usuario": "operador"},
                headers={"set-cookie": "m2_sesion=tok.firmado; HttpOnly; Secure; Path=/"},
            )
        if request.url.path == "/v1/generar":
            if "m2_sesion=tok.firmado" not in request.headers.get("cookie", ""):
                return httpx.Response(401, json={"detail": "Inicia sesión para continuar."})
            return httpx.Response(200, json={"step": "/salidas/pieza.step"})
        return httpx.Response(404)

    return httpx.MockTransport(responder)


def test_humo_inicia_sesion_cuando_la_api_la_exige(tmp_path, monkeypatch):
    """HU-53: con --usuario y M2_SMOKE_CLAVE, el humo entra y genera con la sesión."""
    # Arrange
    llamadas: list[httpx.Request] = []
    monkeypatch.setenv("M2_SMOKE_CLAVE", "clave-humo")

    # Act
    codigo = smoke.main(
        ["--n", "1", "--usuario", "operador", "--salida", str(tmp_path)],
        transport=_transporte_con_sesion(llamadas),
    )

    # Assert
    assert codigo == 0
    assert [r.url.path for r in llamadas] == ["/v1/auth/me", "/v1/auth/login", "/v1/generar"]
    assert json.loads((tmp_path / "smoke.json").read_text(encoding="utf-8"))["validas"] == 1


def test_humo_sin_credenciales_no_gasta_tokens_si_la_api_exige_sesion(
    tmp_path, capsys, monkeypatch
):
    """HU-53: sin credenciales corta antes de generar, con un mensaje accionable."""
    # Arrange
    llamadas: list[httpx.Request] = []
    monkeypatch.delenv("M2_SMOKE_CLAVE", raising=False)
    monkeypatch.delenv("M2_SMOKE_USUARIO", raising=False)

    # Act
    codigo = smoke.main(
        ["--n", "3", "--salida", str(tmp_path)], transport=_transporte_con_sesion(llamadas)
    )

    # Assert
    assert codigo == 2
    assert "/v1/generar" not in [r.url.path for r in llamadas]
    assert "--usuario" in capsys.readouterr().err
    assert not (tmp_path / "smoke.json").exists()


def test_humo_con_clave_incorrecta_no_gasta_tokens(tmp_path, monkeypatch):
    """HU-53: un login rechazado termina con código 2 y sin generar."""
    # Arrange
    llamadas: list[httpx.Request] = []
    monkeypatch.setenv("M2_SMOKE_CLAVE", "mala")

    # Act
    codigo = smoke.main(
        ["--n", "1", "--usuario", "operador", "--salida", str(tmp_path)],
        transport=_transporte_con_sesion(llamadas),
    )

    # Assert
    assert codigo == 2
    assert "/v1/generar" not in [r.url.path for r in llamadas]


def _transporte_sesion_variante(me: httpx.Response | None, login, llamadas: list[str]):
    """Variantes de /v1/auth: `me` fijo y `login` como respuesta o excepción."""

    def responder(request: httpx.Request) -> httpx.Response:
        llamadas.append(request.url.path)
        if request.url.path == "/v1/auth/me":
            return me
        if request.url.path == "/v1/auth/login":
            if isinstance(login, Exception):
                raise login
            return login
        if request.url.path == "/v1/generar":
            return httpx.Response(200, json={"step": "/salidas/pieza.step"})
        return httpx.Response(404)

    return httpx.MockTransport(responder)


REQUERIDA = httpx.Response(200, json={"requerido": True, "autenticado": False})


@pytest.mark.parametrize(
    ("me", "login", "fragmento"),
    [
        (REQUERIDA, httpx.ConnectError("sin red"), "No se pudo iniciar sesión"),
        (httpx.Response(503), None, "No se pudo consultar la sesión"),
        (REQUERIDA, httpx.Response(200, json={"autenticado": True}), "cookie de sesión"),
    ],
    ids=["login-sin-red", "me-5xx", "login-sin-cookie"],
)
def test_humo_termina_con_codigo_2_y_sin_mostrar_la_clave(
    me, login, fragmento, tmp_path, capsys, monkeypatch
):
    """La sesión fallida nunca genera ni imprime la clave."""
    # Arrange
    llamadas: list[str] = []
    monkeypatch.setenv("M2_SMOKE_CLAVE", "clave-secreta-humo")

    # Act
    codigo = smoke.main(
        ["--n", "1", "--usuario", "operador", "--salida", str(tmp_path)],
        transport=_transporte_sesion_variante(me, login, llamadas),
    )

    # Assert
    salida = capsys.readouterr()
    assert codigo == 2
    assert "/v1/generar" not in llamadas
    assert fragmento in salida.err
    assert "clave-secreta-humo" not in salida.out + salida.err


def test_humo_sin_sesion_requerida_no_inicia_sesion(tmp_path, monkeypatch):
    """Modo local (`requerido: false`): genera sin pasar por el login."""
    # Arrange
    llamadas: list[str] = []
    monkeypatch.setenv("M2_SMOKE_CLAVE", "clave-humo")
    me = httpx.Response(200, json={"requerido": False, "autenticado": False})

    # Act
    codigo = smoke.main(
        ["--n", "1", "--usuario", "operador", "--salida", str(tmp_path)],
        transport=_transporte_sesion_variante(me, None, llamadas),
    )

    # Assert
    assert codigo == 0
    assert llamadas == ["/v1/auth/me", "/v1/generar"]


def test_humo_toma_el_usuario_de_m2_smoke_usuario(tmp_path, monkeypatch):
    """Sin --usuario, el usuario sale del entorno."""
    # Arrange
    llamadas: list[httpx.Request] = []
    monkeypatch.setenv("M2_SMOKE_USUARIO", "operador")
    monkeypatch.setenv("M2_SMOKE_CLAVE", "clave-humo")

    # Act
    codigo = smoke.main(
        ["--n", "1", "--salida", str(tmp_path)], transport=_transporte_con_sesion(llamadas)
    )

    # Assert
    assert codigo == 0
    assert json.loads(llamadas[1].content)["usuario"] == "operador"


@pytest.mark.parametrize(
    ("base_url", "avisa"),
    [
        ("http://203.0.113.7:8000", True),
        ("http://127.0.0.1:8000", False),
        ("http://localhost:8000", False),
        ("https://cad.example.org", False),
    ],
)
def test_humo_avisa_si_la_clave_viaja_sin_cifrar(base_url, avisa, tmp_path, capsys, monkeypatch):
    """La clave por HTTP hacia otra máquina viaja en claro: se advierte."""
    # Arrange
    monkeypatch.setenv("M2_SMOKE_CLAVE", "clave-humo")

    # Act
    smoke.main(
        ["--n", "1", "--usuario", "operador", "--base-url", base_url, "--salida", str(tmp_path)],
        transport=_transporte_con_sesion([]),
    )

    # Assert
    assert ("sin cifrar" in capsys.readouterr().err) is avisa
