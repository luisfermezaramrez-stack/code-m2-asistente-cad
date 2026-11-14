"""Solo HTTP SIMULADO: ninguna prueba representa una evaluación real del LLM."""

import json

import httpx
import pytest

from m2_cad.dataset import read_dataset
from m2_cad.evaluacion import (
    CONFORME,
    DECLINACION,
    INDEBIDA,
    NO_CONFORME,
    TECNICO,
    clasificar,
    ejecutar,
)


@pytest.fixture
def placa():
    """Referencia independiente: prisma 40×30×5, volumen 6000 mm³."""
    return {
        "id": "prisma",
        "familia": "plate",
        "solicitud": "Placa de 40 por 30 por 5 mm",
        "resultado_esperado": json.dumps({"volumen_mm3": 6000, "caja_xyz_mm": [40, 30, 5]}),
    }


def construccion(volumen=6000, caja="40x30x5"):
    return {"step": "outputs/simulado/pieza.step", "volumen_mm3": volumen, "caja_mm": caja}


def test_tolerancia_inclusiva_y_por_eje_sin_ordenar(placa):
    for volumen, caja in [(5880, "40x30x5"), (6120, "40.8x29.4x5.1")]:
        assert (
            clasificar(placa, httpx.Response(200, json=construccion(volumen, caja)))[0] == CONFORME
        )
    for volumen, caja in [(6120.01, "40x30x5"), (6000, "30x40x5"), (6000, "40x30x5.1001")]:
        categoria, _, _, silencioso = clasificar(
            placa, httpx.Response(200, json=construccion(volumen, caja))
        )
        assert categoria == NO_CONFORME
        assert silencioso


@pytest.mark.parametrize("caja", ["40x30", "40x30x5x1", "nanx30x5", [True, 30, 5], None])
def test_medidas_invalidas_no_pasan_por_geometria(placa, caja):
    assert clasificar(placa, httpx.Response(200, json=construccion(caja=caja)))[0] == TECNICO


@pytest.mark.parametrize("volumen", ["nan", "inf", 0, -1, True, None])
def test_volumen_invalido(placa, volumen):
    assert clasificar(placa, httpx.Response(200, json=construccion(volumen)))[0] == TECNICO


def test_422_no_equivale_a_declinacion_y_positivo_rechazado_es_indebido(placa):
    negativo = {**placa, "resultado_esperado": "declinar"}
    for respuesta in (
        httpx.Response(422, json={"detail": "programa inválido"}),
        httpx.Response(422, json={"detail": "Pieza declinada: fuera de alcance"}),
        httpx.Response(
            422, headers={"X-Resultado-Tipo": DECLINACION}, json={"detail": "Pieza declinada:   "}
        ),
        httpx.Response(
            503,
            headers={"X-Resultado-Tipo": DECLINACION},
            json={"detail": "Pieza declinada: error de red"},
        ),
    ):
        assert clasificar(negativo, respuesta)[0] == TECNICO
    explicita = httpx.Response(
        422,
        headers={"X-Resultado-Tipo": DECLINACION},
        json={"detail": "Pieza declinada: certificación fuera del alcance"},
    )
    assert clasificar(negativo, explicita)[0] == DECLINACION
    assert clasificar(placa, explicita)[0] == INDEBIDA
    categoria, _, _, silencioso = clasificar(negativo, httpx.Response(200, json=construccion()))
    assert categoria == NO_CONFORME and silencioso


@pytest.mark.parametrize(
    "respuesta",
    [
        httpx.Response(200, content="no json"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={"volumen_mm3": 6000, "caja_mm": "40x30x5"}),
    ],
)
def test_respuesta_rota_es_fallo_tecnico(placa, respuesta):
    assert clasificar(placa, respuesta)[0] == TECNICO


def test_corrida_40_solo_texto_reportes_y_denominadores(tmp_path):
    """Simula 26/30 y 8/10 deliberadamente; NO son métricas del modelo."""
    casos = read_dataset()
    por_texto = {c["solicitud"]: c for c in casos}
    registros = {}
    enviados = []

    def responder(request):
        if request.method == "GET":
            identificador = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(200, json=registros[identificador])
        cuerpo = json.loads(request.content)
        assert request.headers["Accept"] == "application/json"
        assert set(cuerpo) == {"texto"}  # Nunca parámetros ni referencias.
        caso = por_texto[cuerpo["texto"]]
        enviados.append(caso["id"])
        identificador = request.headers["X-Request-ID"]
        registros[identificador] = {"id": identificador, "version": "MODELO-SIMULADO"}
        headers = {"X-Registro-ID": identificador}
        if caso["resultado_esperado"] == "declinar":
            if caso["id"] in ("HU02-N09", "HU02-N10"):
                return httpx.Response(503, json={"detail": "timeout simulado"}, headers=headers)
            return httpx.Response(
                422,
                json={"detail": "Pieza declinada: fuera de alcance"},
                headers={**headers, "X-Resultado-Tipo": DECLINACION},
            )
        esperado = json.loads(caso["resultado_esperado"])
        volumen = esperado["volumen_mm3"]
        if caso["id"] in ("HU02-P27", "HU02-P28", "HU02-P29", "HU02-P30"):
            volumen *= 1.10
        return httpx.Response(
            200, headers=headers, json=construccion(volumen, esperado["caja_xyz_mm"])
        )

    with httpx.Client(
        base_url="http://simulado", transport=httpx.MockTransport(responder)
    ) as client:
        reporte, carpeta = ejecutar(client, salida=tmp_path, simulado=True)
    resumen = reporte["resumen"]
    assert len(enviados) == len(set(enviados)) == 40
    assert (resumen["conformes"], resumen["positivos"]) == (26, 30)
    assert (resumen["declinaciones_correctas"], resumen["negativos"]) == (8, 10)
    assert resumen["cumple_metas"]
    assert resumen["errores_silenciosos"] == 4
    assert resumen["registros_confirmados"] == 40
    assert resumen["por_familia"]["tornillería"][NO_CONFORME] == 4
    filas = reporte["casos"]
    assert all(f["step"] == "no aplica" for f in filas if f["categoria"] == DECLINACION)
    assert all(f["step"].endswith("/step") for f in filas if f["categoria"] == CONFORME)
    contenido = (carpeta / "reporte.md").read_text(encoding="utf-8")
    assert "SIMULADO" in contenido and "26/30" in contenido and "8/10" in contenido
    assert all(f["registro_url"] in contenido for f in filas)
    assert json.loads((carpeta / "resultados.json").read_text(encoding="utf-8")) == reporte


def test_todos_los_timeouts_conservan_40_casos_y_no_inventan_registros(tmp_path):
    def timeout(request):
        raise httpx.ReadTimeout("SIMULADO", request=request)

    with httpx.Client(base_url="http://simulado", transport=httpx.MockTransport(timeout)) as client:
        reporte, _ = ejecutar(client, salida=tmp_path, simulado=True)
    assert len(reporte["casos"]) == 40
    assert all(f["categoria"] == TECNICO and not f["registro_confirmado"] for f in reporte["casos"])
    assert reporte["resumen"]["positivos"] == 30
    assert reporte["resumen"]["negativos"] == 10
    assert not reporte["resumen"]["cumple_metas"]
    assert reporte["resumen"]["conformes"] == reporte["resumen"]["declinaciones_correctas"] == 0


def test_evaluador_y_api_actual_40_registros_unicos_sin_modelo(tmp_path, monkeypatch):
    """Pipeline SIMULADO; contratos HTTP/CSV y enlaces reales, sin llamar al LLM."""
    import csv

    from fastapi.testclient import TestClient

    from m2_cad import api, seguimiento

    monkeypatch.chdir(tmp_path)
    ruta = tmp_path / "registro.csv"
    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: ruta)
    step = tmp_path / "outputs" / "pieza.step"
    step.parent.mkdir()
    step.write_text("STEP SIMULADO", encoding="utf-8")
    casos = {c["solicitud"]: c for c in read_dataset()}

    def simular(texto, medicion=None):
        caso = casos[texto]
        if caso["resultado_esperado"] == "declinar":
            raise api.DeclinacionSolicitud("fuera del catálogo (SIMULADO)")
        esperado = json.loads(caso["resultado_esperado"])
        return {
            "step": str(step),
            "volumen_mm3": str(esperado["volumen_mm3"]),
            "caja_mm": "x".join(map(str, esperado["caja_xyz_mm"])),
        }

    api.app.dependency_overrides[api.obtener_procesador] = lambda: simular
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: (
        seguimiento.Configuracion(activo=False)
    )
    try:
        with TestClient(api.app) as cliente:
            reporte, _ = ejecutar(cliente, salida=tmp_path / "reportes", simulado=True)
            for fila in reporte["casos"]:
                assert fila["registro_confirmado"] and fila["correlacion_respuesta"]
                if fila["positivo"]:
                    assert cliente.get(fila["step"]).text == "STEP SIMULADO"
        with ruta.open(newline="", encoding="utf-8") as archivo:
            filas = list(csv.DictReader(archivo))
        assert len(filas) == len({f["id"] for f in filas}) == 40
        assert all(f["traduccion"] == "no aplica" for f in filas)
        assert reporte["resumen"]["conformes"] == 30
        assert reporte["resumen"]["declinaciones_correctas"] == 10
    finally:
        api.app.dependency_overrides.pop(api.obtener_procesador, None)
        api.app.dependency_overrides.pop(api.obtener_configuracion_seguimiento, None)


def test_timeout_cli_invalido(monkeypatch):
    from m2_cad import evaluacion

    monkeypatch.setattr("sys.argv", ["evaluacion", "--timeout", "nan"])
    with pytest.raises(SystemExit) as exc:
        evaluacion.main()
    assert exc.value.code == 2


@pytest.mark.parametrize(
    "cumple,registros,esperado", [(True, 40, 0), (True, 39, 2), (False, 40, 2)]
)
def test_salida_cli(monkeypatch, tmp_path, capsys, cumple, registros, esperado):
    from m2_cad import evaluacion

    monkeypatch.setattr("sys.argv", ["evaluacion"])
    monkeypatch.setattr(
        evaluacion,
        "ejecutar",
        lambda *a, **k: (
            {"resumen": {"cumple_metas": cumple, "registros_confirmados": registros}},
            tmp_path,
        ),
    )
    assert evaluacion.main() == esperado
    assert "Reporte:" in capsys.readouterr().out
