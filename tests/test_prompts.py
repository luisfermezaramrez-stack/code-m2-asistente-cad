"""Pruebas del prompt versionado como artefacto (HU-33, SPEC-034).

Sin red, sin GPU y sin API key: el modelo se simula.
- AC1: la fila del registro lleva el id y el hash del prompt usado.
- AC2: cambiar el contenido sin subir la versión hace fallar la verificación.
- AC3: el pipeline carga el prompt por id y su hash coincide con el archivo.
- RNF-2: la primera versión es idéntica a `PROMPT_SISTEMA` (la migración no
  cambia lo que recibe el modelo).
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from m2_cad import prompts
from m2_cad.registro import CAMPOS, SIN_PROMPT, registrar

RAIZ = Path(__file__).resolve().parents[1]
CARPETA_PROMPTS = RAIZ / "prompts"
ARCHIVO_VIGENTE = "planner-v1.txt"


def _cargado(ruta: Path) -> str:
    """Texto cargado de un archivo de prompt: contenido menos un salto final."""
    contenido = ruta.read_text(encoding="utf-8")
    return contenido[:-1] if contenido.endswith("\n") else contenido


def _manifiesto(entradas: list[dict[str, object]]) -> str:
    """Arma un manifiesto TOML con las entradas dadas (para árboles sintéticos)."""
    lineas = ["version = 1", ""]
    for entrada in entradas:
        lineas.append("[[prompts]]")
        lineas.extend(f"{clave} = {json.dumps(valor)}" for clave, valor in entrada.items())
        lineas.append("")
    return "\n".join(lineas)


def _entrada(version: int, texto: str, *, archivo: str, vigente: bool = True) -> dict:
    """Entrada de manifiesto completa con el hash calculado del texto dado."""
    return {
        "id": "planner",
        "version": version,
        "archivo": archivo,
        "sha256": prompts.sha256_texto(texto),
        "descripcion": f"prompt v{version}",
        "vigente": vigente,
    }


def _arbol(
    raiz: Path, textos: dict[str, str], entradas: list[dict[str, object]] | None = None
) -> Path:
    """Crea un árbol prompts/ sintético: cada texto queda como archivo con \\n final."""
    raiz.mkdir(parents=True, exist_ok=True)
    for archivo, texto in textos.items():
        (raiz / archivo).write_text(texto + "\n", encoding="utf-8")
    (raiz / prompts.MANIFIESTO).write_text(_manifiesto(entradas or []), encoding="utf-8")
    return raiz


def _leer(ruta: Path) -> list[dict[str, str]]:
    with ruta.open(newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def test_el_manifiesto_del_repositorio_esta_consistente():
    """AC2/RNF-1: el árbol real no tiene ningún error de integridad."""
    assert prompts.verificar() == []


def test_cargar_devuelve_el_prompt_vigente_con_id_version_y_hash():
    """RF-1/AC3: el prompt se carga por id y el hash coincide con el archivo."""
    prompt = prompts.cargar()

    assert prompts.PROMPT_VIGENTE == "planner"
    assert prompts.RUTA_PROMPTS == CARPETA_PROMPTS
    assert prompts.LONGITUD_SHA256 == 64
    assert prompt.id == prompts.PROMPT_VIGENTE
    assert prompt.version == 1
    assert prompt.etiqueta == "planner-v1"
    assert prompt.archivo == ARCHIVO_VIGENTE
    # El texto cargado es el archivo menos exactamente un salto de línea.
    assert (CARPETA_PROMPTS / prompt.archivo).read_text(encoding="utf-8") == prompt.texto + "\n"
    assert prompt.texto == _cargado(CARPETA_PROMPTS / prompt.archivo)
    assert prompt.sha256 == prompts.sha256_texto(prompt.texto)
    assert prompt.sha256 == hashlib.sha256(prompt.texto.encode("utf-8")).hexdigest()
    assert len(prompt.sha256) == prompts.LONGITUD_SHA256

    manifiesto = prompts.cargar_manifiesto()
    assert manifiesto["version"] == 1
    vigentes = [
        entrada
        for entrada in manifiesto["prompts"]
        if entrada["id"] == prompts.PROMPT_VIGENTE and entrada["vigente"]
    ]
    assert len(vigentes) == 1
    assert vigentes[0]["archivo"] == prompt.archivo
    assert vigentes[0]["version"] == prompt.version
    assert vigentes[0]["sha256"] == prompt.sha256


def test_listar_devuelve_todas_las_entradas_declaradas(tmp_path):
    """RF-1: el manifiesto declara una versión por entrada, sin duplicarlas."""
    raiz = _arbol(
        tmp_path / "prompts",
        {"planner-v1.txt": "texto uno", "planner-v2.txt": "texto dos"},
        [
            _entrada(1, "texto uno", archivo="planner-v1.txt", vigente=False),
            _entrada(2, "texto dos", archivo="planner-v2.txt"),
        ],
    )

    listados = prompts.listar(raiz=raiz)

    assert [(prompt.etiqueta, prompt.texto) for prompt in listados] == [
        ("planner-v1", "texto uno"),
        ("planner-v2", "texto dos"),
    ]


def test_rnf2_el_prompt_del_pipeline_es_el_archivo_vigente():
    """RNF-2: la migración no cambia el texto que recibe el modelo."""
    from m2_cad import pipeline

    prompt = prompts.cargar()

    assert pipeline.PROMPT_SISTEMA == prompt.texto
    assert pipeline.PROMPT_VIGENTE == prompt
    assert prompt.id == pipeline.PROMPT_VIGENTE.id
    assert prompt.version == pipeline.PROMPT_VIGENTE.version
    assert prompt.sha256 == pipeline.PROMPT_VIGENTE.sha256
    # HU-14 sigue cubierto: el archivo conserva el catálogo y las reglas del prompt.
    for tipo in pipeline.CATALOGO:
        assert f"{tipo}{{" in prompt.texto, tipo
    assert "Spanish" in prompt.texto
    assert "JSON" in prompt.texto
    assert "unsupported" in prompt.texto


def test_ac3_el_pipeline_envia_el_prompt_cargado_y_no_una_cadena_inline(tmp_path, monkeypatch):
    """AC3/RF-2/S6: con el modelo simulado, el sistema es el archivo versionado."""
    pytest.importorskip("cadquery")
    from m2_cad import llm_resiliente, pipeline

    enviado: dict = {}

    def consultar_falso(cuerpo, **resto):
        enviado["cuerpo"] = cuerpo
        programa = {
            "parts": [
                {
                    "id": "p",
                    "type": "spacer",
                    "material": "steel",
                    "params": {"outer_d": 14, "bore_d": 0, "height": 10},
                }
            ],
            "mates": [],
        }
        return {
            "model": "modelo-simulado",
            "choices": [{"message": {"content": json.dumps(programa)}}],
        }

    # Sin red: se sustituye la llamada al proveedor y la URL deja de ser la real.
    monkeypatch.setenv("LLM_BASE_URL", "http://modelo-simulado-no-contactado")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(llm_resiliente, "consultar", consultar_falso)

    resultado = pipeline.generar_pieza("Espaciador de 14 mm", directorio=tmp_path)

    prompt = prompts.cargar()
    assert enviado["cuerpo"]["messages"][0] == {"role": "system", "content": prompt.texto}
    assert enviado["cuerpo"]["messages"][1] == {
        "role": "user",
        "content": "Espaciador de 14 mm",
    }
    # Id, versión y hash del prompt usado salen del archivo, no del código.
    assert prompt.id == pipeline.PROMPT_VIGENTE.id
    assert prompt.version == pipeline.PROMPT_VIGENTE.version
    assert prompt.sha256 == pipeline.PROMPT_VIGENTE.sha256
    assert prompt.sha256 == prompts.sha256_texto(
        (CARPETA_PROMPTS / prompt.archivo).read_text(encoding="utf-8")[:-1]
    )
    assert resultado.step.exists() and resultado.glb.exists()
    assert resultado.familia == "spacer"


def test_ac1_el_registro_persiste_prompt_y_hash(tmp_path):
    """AC1/S8: la fila lleva el id y el hash del prompt usado."""
    ruta = tmp_path / "registro.csv"
    prompt = prompts.cargar()

    fila = registrar(
        texto="Espaciador de 14 mm",
        traduccion="no aplica",
        resultado="{}",
        latencia_ms=12.0,
        version="modelo-simulado",
        ruta=ruta,
        prompt=prompt.etiqueta,
        prompt_hash=prompt.sha256,
    )

    assert CAMPOS[-2:] == ["prompt", "prompt_hash"]
    assert set(fila) == set(CAMPOS)
    assert fila["prompt"] == "planner-v1"
    assert fila["prompt_hash"] == prompt.sha256
    filas = _leer(ruta)
    assert filas[0]["prompt"] == prompt.etiqueta
    assert filas[0]["prompt_hash"] == prompt.sha256


def test_ac1_sin_prompt_la_fila_escribe_el_marcador(tmp_path):
    """S8/SPEC-004 AC3: sin prompt conocido la fila nunca queda vacía."""
    ruta = tmp_path / "registro.csv"

    fila = registrar(
        texto="placa",
        traduccion="no aplica",
        resultado=None,
        latencia_ms=1.0,
        ruta=ruta,
        prompt="",
        prompt_hash=None,
    )

    assert SIN_PROMPT == "no aplica"
    assert fila["prompt"] == SIN_PROMPT
    assert fila["prompt_hash"] == SIN_PROMPT
    assert all(valor != "" for valor in fila.values())
    filas = _leer(ruta)
    assert filas[0]["prompt"] == SIN_PROMPT
    assert filas[0]["prompt_hash"] == SIN_PROMPT


def test_ac2_un_cambio_de_texto_sin_subir_version_falla_la_verificacion(tmp_path):
    """AC2/S10: mutar el contenido sin subir la versión deja el chequeo en error."""
    copia = tmp_path / "prompts"
    shutil.copytree(CARPETA_PROMPTS, copia)
    original = prompts.cargar(raiz=copia)
    declarado = original.sha256

    mutado = original.texto + " Cambio aplicado sin subir la versión."
    (copia / original.archivo).write_text(mutado + "\n", encoding="utf-8")

    errores = prompts.verificar(raiz=copia)

    assert len(errores) == 1
    error = errores[0]
    assert original.archivo in error
    assert f"versión {original.version}" in error
    assert declarado in error
    assert prompts.sha256_texto(mutado) in error
    assert "sube `version`" in error


def test_ac2_subir_la_version_con_un_archivo_nuevo_vuelve_a_estar_limpio(tmp_path):
    """AC2: una versión nueva es un archivo nuevo más una entrada nueva."""
    copia = tmp_path / "prompts"
    shutil.copytree(CARPETA_PROMPTS, copia)
    original = prompts.cargar(raiz=copia)
    mutado = original.texto + " Cambio aplicado sin subir la versión."
    assert prompts.verificar(raiz=copia) == []

    # Bump real: el archivo nuevo lleva el texto nuevo; la v1 no se toca.
    (copia / "planner-v2.txt").write_text(mutado + "\n", encoding="utf-8")
    (copia / prompts.MANIFIESTO).write_text(
        _manifiesto(
            [
                _entrada(original.version, original.texto, archivo=original.archivo, vigente=False),
                _entrada(2, mutado, archivo="planner-v2.txt"),
            ]
        ),
        encoding="utf-8",
    )

    assert prompts.verificar(raiz=copia) == []
    vigente = prompts.cargar(raiz=copia)
    assert vigente.etiqueta == "planner-v2"
    assert vigente.sha256 == prompts.sha256_texto(mutado)


def test_verificar_detecta_version_duplicada(tmp_path):
    """RF-5: dos entradas con el mismo id y versión son un error del manifiesto."""
    raiz = _arbol(
        tmp_path / "prompts",
        {"planner-v1.txt": "texto uno", "planner-v1b.txt": "texto uno"},
        [
            _entrada(1, "texto uno", archivo="planner-v1.txt", vigente=False),
            _entrada(1, "texto uno", archivo="planner-v1b.txt"),
        ],
    )

    errores = prompts.verificar(raiz=raiz)

    assert len(errores) == 1
    assert "duplicada" in errores[0]
    assert "planner" in errores[0] and "1" in errores[0]


@pytest.mark.parametrize("vigentes", [0, 2], ids=["sin-vigente", "dos-vigentes"])
def test_verificar_exige_exactamente_un_vigente_por_id(tmp_path, vigentes):
    """RF-1: cada id declara exactamente una entrada vigente."""
    raiz = _arbol(
        tmp_path / "prompts",
        {"planner-v1.txt": "texto uno", "planner-v2.txt": "texto dos"},
        [
            _entrada(1, "texto uno", archivo="planner-v1.txt", vigente=vigentes >= 1),
            _entrada(2, "texto dos", archivo="planner-v2.txt", vigente=vigentes >= 2),
        ],
    )

    errores = prompts.verificar(raiz=raiz)

    assert len(errores) == 1
    assert "vigente" in errores[0]
    assert "planner" in errores[0]


def test_verificar_detecta_sha256_con_formato_invalido(tmp_path):
    """RF-1: el sha256 declarado es hexadecimal de 64 caracteres."""
    entrada = _entrada(1, "texto uno", archivo="planner-v1.txt")
    entrada["sha256"] = "abc"
    raiz = _arbol(tmp_path / "prompts", {"planner-v1.txt": "texto uno"}, [entrada])

    errores = prompts.verificar(raiz=raiz)

    assert len(errores) == 1
    assert "sha256" in errores[0]
    assert "planner-v1.txt" in errores[0]


def test_verificar_detecta_un_archivo_faltante(tmp_path):
    """RF-5: una entrada que apunta a un archivo inexistente es un error."""
    raiz = _arbol(
        tmp_path / "prompts",
        {"planner-v1.txt": "texto uno"},
        [_entrada(1, "texto uno", archivo="planner-v9.txt")],
    )

    errores = prompts.verificar(raiz=raiz)

    assert len(errores) == 1
    assert "planner-v9.txt" in errores[0]
    assert "versión 1" in errores[0]


def test_verificar_sin_manifiesto_devuelve_error_sin_lanzar(tmp_path):
    """RF-5: la verificación nunca lanza por un problema del manifiesto."""
    errores = prompts.verificar(raiz=tmp_path)

    assert len(errores) == 1
    assert prompts.MANIFIESTO in errores[0]


def test_verificar_detecta_una_entrada_sin_clave_requerida(tmp_path):
    """RF-5: una entrada incompleta se reporta como error, no se ignora."""
    entrada = _entrada(1, "texto uno", archivo="planner-v1.txt")
    del entrada["archivo"]
    raiz = _arbol(tmp_path / "prompts", {"planner-v1.txt": "texto uno"}, [entrada])

    errores = prompts.verificar(raiz=raiz)

    assert len(errores) == 1
    assert "archivo" in errores[0]


def test_cargar_rechaza_un_id_desconocido(tmp_path):
    """RF-1: el cargador solo conoce los ids declarados en el manifiesto."""
    raiz = _arbol(
        tmp_path / "prompts",
        {"planner-v1.txt": "texto uno"},
        [_entrada(1, "texto uno", archivo="planner-v1.txt")],
    )

    with pytest.raises(prompts.ErrorPrompt, match="inexistente"):
        prompts.cargar("inexistente", raiz=raiz)


def test_cargar_rechaza_un_manifiesto_ausente(tmp_path):
    """RF-1: sin manifiesto no hay prompt vigente que cargar."""
    with pytest.raises(prompts.ErrorPrompt, match=prompts.MANIFIESTO):
        prompts.cargar(raiz=tmp_path)


def test_cargar_rechaza_un_archivo_ausente(tmp_path):
    """RF-1: el archivo declarado tiene que existir."""
    raiz = _arbol(
        tmp_path / "prompts",
        {"planner-v1.txt": "texto uno"},
        [_entrada(1, "texto uno", archivo="planner-v9.txt")],
    )

    with pytest.raises(prompts.ErrorPrompt, match="planner-v9.txt"):
        prompts.cargar(raiz=raiz)


def test_cargar_rechaza_un_hash_alterado_en_el_manifiesto(tmp_path):
    """RF-1/AC2: el cargador valida el hash, no solo la verificación de CI."""
    entrada = _entrada(1, "texto uno", archivo="planner-v1.txt")
    entrada["sha256"] = "0" * prompts.LONGITUD_SHA256
    raiz = _arbol(tmp_path / "prompts", {"planner-v1.txt": "texto uno"}, [entrada])

    with pytest.raises(prompts.ErrorPrompt) as excinfo:
        prompts.cargar(raiz=raiz)

    mensaje = str(excinfo.value)
    assert "planner-v1.txt" in mensaje
    assert "versión 1" in mensaje
    assert "0" * prompts.LONGITUD_SHA256 in mensaje
    assert prompts.sha256_texto("texto uno") in mensaje


def test_cargar_rechaza_una_entrada_mal_formada(tmp_path):
    """RF-1: una entrada sin clave requerida es ErrorPrompt, no KeyError."""
    entrada = _entrada(1, "texto uno", archivo="planner-v1.txt")
    del entrada["sha256"]
    raiz = _arbol(tmp_path / "prompts", {"planner-v1.txt": "texto uno"}, [entrada])

    with pytest.raises(prompts.ErrorPrompt, match="sha256"):
        prompts.cargar(raiz=raiz)


def test_la_imagen_copia_los_artefactos_que_el_pipeline_lee_al_importar():
    """El prompt se carga al importar el pipeline: la imagen debe traerlo (HU-10)."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[1]
    dockerfile = (raiz / "Dockerfile").read_text(encoding="utf-8")

    for directorio in ("prompts", "data"):
        assert f"COPY {directorio} ./{directorio}" in dockerfile, (
            f"la imagen no copia {directorio}/ y el módulo lo lee en tiempo de import"
        )
