"""Comparación A/B de prompts y modelos (HU-52 / SPEC-053), sin red, key ni MLflow."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("cadquery")

from m2_cad import ab, banco_replay, dataset, pipeline, prompts  # noqa: E402

IDS = ("HU02-P01", "HU02-P02", "HU02-N01", "HU02-N02")


@pytest.fixture(autouse=True)
def _aislar(monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_ENABLED", "0")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)


class CorridaFalsa:
    def __init__(self, nombre, tags, configuracion):
        self.nombre = nombre
        self.tags = tags
        self.configuracion = configuracion
        self.parametros = {}
        self.metricas = {}
        self.estado = None
        self.error = None

    def registrar_params(self, **valores):
        self.parametros.update(valores)

    def registrar_metricas(self, **valores):
        self.metricas.update(valores)

    def finalizar(self, *, estado, error=None):
        self.estado = estado
        self.error = error


def _filas():
    filas = [fila for fila in dataset.read_dataset() if fila["id"] in IDS]
    assert len(filas) == len(IDS)
    return filas


def _variantes():
    return (
        ab.construir_variante("A", "planner-v1", "modelo-a"),
        ab.construir_variante("B", "planner-v2", "modelo-b"),
    )


def _seguimiento(monkeypatch):
    corridas = []

    def iniciar(experimento, *, nombre, tags, configuracion):
        corrida = CorridaFalsa(nombre, tags, configuracion)
        corridas.append((experimento, corrida))
        return corrida

    monkeypatch.setattr(ab.seguimiento, "iniciar_corrida", iniciar)
    return corridas


def _evaluador(monkeypatch, variantes, vistos):
    texto_b = variantes[1].prompt.texto

    def evaluar(fila, *, directorio, configuracion=None):
        vistos.append((pipeline.PROMPT_SISTEMA, pipeline.llm.planner_model()))
        declinar = fila["resultado_esperado"] == "declinar"
        correcto, estado, detalle = True, ("declinada" if declinar else "construida"), "ok"
        if pipeline.PROMPT_SISTEMA == texto_b:
            if fila["id"] == "HU02-P02":
                correcto, estado, detalle = False, "rechazada", "rechazo variante B"
            if fila["id"] == "HU02-N01":
                correcto, estado, detalle = False, "construida", "silencio variante B"
        return {
            "id": fila["id"],
            "familia": fila["familia"],
            "esperado": "declinar" if declinar else "aceptar",
            "estado": estado,
            "correcto": correcto,
            "latencia_s": 0.1,
            "tokens_entrada": 100,
            "tokens_salida": 20,
            "detalle": detalle,
        }

    monkeypatch.setattr(ab.banco, "evaluar_caso", evaluar)


def _correr(monkeypatch, tmp_path, variantes=None, filas=None):
    a, b = variantes or _variantes()
    filas = filas if filas is not None else _filas()
    vistos = []
    _evaluador(monkeypatch, (a, b), vistos)
    resultados = [
        ab.ejecutar_variante(
            variante, filas, id_comparacion="cmp-52", salida=tmp_path / variante.etiqueta
        )
        for variante in (a, b)
    ]
    return resultados, vistos, ab.validar_variantes(a, b, filas)


def test_ac1_dos_corridas_mlflow_con_trazabilidad(monkeypatch, tmp_path):
    corridas = _seguimiento(monkeypatch)
    resultados, _, _ = _correr(monkeypatch, tmp_path)

    assert len(corridas) == 2
    assert corridas[0][0] == corridas[1][0] == ab.EXPERIMENTO_AB
    assert [corrida.tags["variante"] for _, corrida in corridas] == ["A", "B"]
    assert [corrida.tags["prompt_version"] for _, corrida in corridas] == [
        "planner-v1",
        "planner-v2",
    ]
    assert [corrida.tags["prompt_sha256"] for _, corrida in corridas] == [
        resultados[0]["prompt"]["sha256"],
        resultados[1]["prompt"]["sha256"],
    ]
    assert all(corrida.tags["comparacion_id"] == "cmp-52" for _, corrida in corridas)
    assert [corrida.parametros["modelo"] for _, corrida in corridas] == [
        "modelo-a",
        "modelo-b",
    ]
    assert all(corrida.estado == "completado" for _, corrida in corridas)
    assert all("acierto" in corrida.metricas for _, corrida in corridas)


def test_ac2_reporte_por_familia_y_casos_cambiados(monkeypatch, tmp_path):
    _seguimiento(monkeypatch)
    resultados, _, contexto = _correr(monkeypatch, tmp_path)
    comparacion = ab.comparar(resultados, id_comparacion="cmp-52", contexto=contexto)

    assert comparacion["por_familia"]["plate"]["A"]["piezas_conformes"] == 2
    assert comparacion["por_familia"]["plate"]["B"]["piezas_conformes"] == 1
    fuera = comparacion["por_familia"]["fuera_alcance"]
    assert fuera["A"]["declinaciones_correctas"] == 2
    assert fuera["B"]["declinaciones_correctas"] == 1
    assert fuera["B"]["errores_silenciosos"] == 1
    assert [caso["id"] for caso in comparacion["casos_cambiados"]] == [
        "HU02-N01",
        "HU02-P02",
    ]

    reporte = ab.markdown(comparacion)
    assert "## Familia: plate" in reporte
    assert "## Familia: fuera_alcance" in reporte
    assert "HU02-P02" in reporte and "HU02-N01" in reporte
    rutas = ab.escribir(comparacion, tmp_path / "reporte")
    assert Path(rutas["markdown"]).exists() and Path(rutas["json"]).exists()
    assert "ganador" not in comparacion and "promovida" not in comparacion
    assert comparacion["promocion"].startswith("decisión explícita")


def test_ac3_prompt_y_modelo_se_fijan_y_se_restauran(monkeypatch, tmp_path):
    _seguimiento(monkeypatch)
    a, b = _variantes()
    prompt_original, modelo_original = pipeline.PROMPT_SISTEMA, pipeline.llm.planner_model
    chat_original, url_original = pipeline.llm.chat, pipeline.llm.base_url

    _, vistos, _ = _correr(monkeypatch, tmp_path)

    assert {prompt for prompt, _ in vistos} == {a.prompt.texto, b.prompt.texto}
    assert [modelo for prompt, modelo in vistos if prompt == a.prompt.texto] == ["modelo-a"] * 4
    assert [modelo for prompt, modelo in vistos if prompt == b.prompt.texto] == ["modelo-b"] * 4
    assert pipeline.PROMPT_SISTEMA == prompt_original
    assert pipeline.llm.planner_model is modelo_original
    assert pipeline.llm.chat is chat_original
    assert pipeline.llm.base_url == url_original


def test_cargar_version_registrada_y_rechazar_inexistente():
    """SPEC-034 sigue intacta: la v2 existe sin desplazar a la vigente (AC3)."""
    assert prompts.cargar().version == 1
    version_dos = prompts.cargar_version("planner", 2)
    assert version_dos.etiqueta == "planner-v2"
    assert version_dos.sha256 == prompts.sha256_texto(version_dos.texto)
    with pytest.raises(prompts.ErrorPrompt, match="no declara"):
        prompts.cargar_version("planner", 99)


def test_rnf_mismo_banco_temperatura_y_variantes_distintas():
    a, b = _variantes()
    filas = _filas()
    contexto = ab.validar_variantes(a, b, filas)

    assert contexto["temperatura"] == pipeline.TEMPERATURA_LLM
    assert contexto["casos"] == len(filas)
    assert contexto["prompt_vigente"] == "planner-v1"
    assert contexto["modo"] == "real"
    with pytest.raises(ab.ErrorAB, match="idénticas"):
        ab.validar_variantes(a, replace(b, prompt=a.prompt, modelo=a.modelo), filas)
    with pytest.raises(ab.ErrorAB, match="replay"):
        ab.validar_variantes(replace(a, replay=Path("a.json")), b, filas)


def _artefacto_replay(tmp_path: Path, variante, filas: list[dict]) -> Path:
    with ab._variante_activa(variante):
        datos = banco_replay.sembrar(filas, modelo=variante.modelo)
    datos["prompt"] = ab.identidad_prompt(variante.prompt)
    for respuesta in datos["respuestas"]:
        respuesta["prompt_version"] = variante.prompt.etiqueta
    return banco_replay.escribir(datos, tmp_path / f"{variante.etiqueta}.json")


def test_replay_por_variante_y_rechazo_de_artefacto_ajeno(monkeypatch, tmp_path):
    """RF-5/RNF-1: cada variante lee sus respuestas; una grabación ajena falla antes de correr."""
    _seguimiento(monkeypatch)
    a, b = _variantes()
    filas = _filas()
    ruta_a = _artefacto_replay(tmp_path, a, filas)
    ruta_b = _artefacto_replay(tmp_path, b, filas)
    a, b = replace(a, replay=ruta_a), replace(b, replay=ruta_b)

    contexto = ab.validar_variantes(a, b, filas)
    assert contexto["modo"] == "replay"

    def sin_red(*args, **kwargs):
        raise AssertionError("la comparación en replay intentó abrir red")

    monkeypatch.setattr(pipeline.llm, "chat", sin_red)
    resultados, _, _ = _correr(monkeypatch, tmp_path, variantes=(a, b), filas=filas)
    assert [resultado["modo"] for resultado in resultados] == ["replay", "replay"]

    datos = json.loads(ruta_b.read_text(encoding="utf-8"))
    datos["modelo"] = "modelo-ajeno"
    ruta_ajena = tmp_path / "ajena.json"
    ruta_ajena.write_text(json.dumps(datos, indent=2), encoding="utf-8")
    with pytest.raises(ab.ErrorAB, match="modelo"):
        ab.ejecutar_variante(
            replace(b, replay=ruta_ajena),
            filas,
            id_comparacion="cmp-52",
            salida=tmp_path / "fallo",
        )
