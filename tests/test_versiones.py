"""Pruebas del almacén de versiones y del diff de programas (HU-35, SPEC-036).

Sin red, sin GPU y sin API key: biblioteca estándar y `tmp_path`.
- S2/RF-2: el diff estructura el cambio entre dos programas DSL.
- S4/RF-4: una edición verificada suma una versión y conserva las anteriores.
- S5/RF-5: el historial se consulta en orden, por solicitud.
- S9/RNF-3: cada versión guarda el prompt y su hash.
"""

from __future__ import annotations

import json

import pytest

from m2_cad import versiones

ID_UNO = "0123456789abcdef0123456789abcdef"
ID_DOS = "fedcba9876543210fedcba9876543210"
ID_GUIONES = "01234567-89ab-cdef-0123-456789abcdef"

PROGRAMA = {
    "parts": [
        {
            "id": "p",
            "type": "plate",
            "material": "steel",
            "params": {"width": 80, "depth": 60, "thick": 5},
        }
    ],
    "mates": [],
}


def _programa(**params: float) -> dict:
    """Programa de una sola placa con los parámetros dados."""
    return {
        "parts": [
            {"id": "p", "type": "plate", "material": "steel", "params": dict(params)},
        ],
        "mates": [],
    }


def _registrar(solicitud_id: str = ID_UNO, **extra) -> dict:
    """Versión verificada mínima con los campos obligatorios del almacén."""
    datos = {
        "usuario": "ana",
        "programa": PROGRAMA,
        "artefactos": ["pieza.step", "pieza.glb", "pieza.csv"],
        "prompt": "editor-v1",
        "prompt_hash": "a" * 64,
    }
    datos.update(extra)
    return versiones.registrar_version(solicitud_id, **datos)


# --- Diff -------------------------------------------------------------------


def test_el_diff_reporta_un_numero_cambiado():
    """S2/RF-2: el cambio de un número aparece con su ruta y sus dos valores."""
    previo = _programa(width=80, depth=60, thick=5)
    nuevo = _programa(width=80, depth=60, thick=10)

    assert versiones.diff_programas(previo, nuevo) == [
        {"ruta": "parts[0].params.thick", "antes": 5, "despues": 10}
    ]


def test_el_diff_reporta_una_clave_agregada_sin_antes():
    """S2: una clave nueva llega sin `antes`."""
    previo = _programa(width=80, depth=60, thick=5)
    nuevo = _programa(width=80, depth=60, thick=5, boss_d=20)

    assert versiones.diff_programas(previo, nuevo) == [
        {"ruta": "parts[0].params.boss_d", "despues": 20}
    ]


def test_el_diff_reporta_una_clave_quitada_sin_despues():
    """S2: una clave eliminada llega sin `despues`."""
    previo = _programa(width=80, depth=60, thick=5, boss_d=20)
    nuevo = _programa(width=80, depth=60, thick=5)

    assert versiones.diff_programas(previo, nuevo) == [
        {"ruta": "parts[0].params.boss_d", "antes": 20}
    ]


def test_el_diff_recorre_una_lista_por_indice():
    """S2: la ruta nombra el índice de la lista (`parts[0].params.thick`)."""
    previo = {"parts": [{"type": "plate", "params": {"thick": 5}}], "mates": []}
    nuevo = {"parts": [{"type": "plate", "params": {"thick": 8}}], "mates": []}

    assert versiones.diff_programas(previo, nuevo) == [
        {"ruta": "parts[0].params.thick", "antes": 5, "despues": 8}
    ]


def test_el_diff_de_programas_iguales_es_vacio():
    """S2: sin cambios no se inventa ninguna entrada."""
    assert versiones.diff_programas(PROGRAMA, json.loads(json.dumps(PROGRAMA))) == []


def test_el_diff_es_determinista():
    """S2: el mismo par de programas da siempre la misma lista, en el mismo orden."""
    previo = _programa(width=80, depth=60, thick=5)
    nuevo = _programa(width=90, depth=60, thick=10)

    primero = versiones.diff_programas(previo, nuevo)
    segundo = versiones.diff_programas(
        json.loads(json.dumps(previo)), json.loads(json.dumps(nuevo))
    )

    assert primero == segundo
    assert [cambio["ruta"] for cambio in primero] == [
        "parts[0].params.thick",
        "parts[0].params.width",
    ]


# --- Índice de versiones ----------------------------------------------------


def test_registrar_version_agrega_v1_v2_v3_en_orden(tmp_path):
    """S4/S5: cada edición verificada suma la siguiente versión del historial."""
    primera = _registrar(directorio=tmp_path)
    segunda = _registrar(directorio=tmp_path)
    tercera = _registrar(directorio=tmp_path)

    assert [primera["version"], segunda["version"], tercera["version"]] == [1, 2, 3]
    assert segunda["hora"] >= primera["hora"]
    assert segunda["programa"] == PROGRAMA
    assert segunda["artefactos"] == ["pieza.step", "pieza.glb", "pieza.csv"]
    assert segunda["diff"] == []
    assert segunda["prompt"] == "editor-v1" and segunda["prompt_hash"] == "a" * 64
    assert segunda["usuario"] == "ana"
    assert "causa" not in segunda
    assert versiones.leer_versiones(ID_UNO, directorio=tmp_path) == [
        primera,
        segunda,
        tercera,
    ]
    assert (tmp_path / f"{ID_UNO}.json").exists()


def test_leer_versiones_ordena_por_numero_de_version(tmp_path):
    """S5: el historial se devuelve en orden ascendente aunque se escriba desordenado."""
    _registrar(version=2, directorio=tmp_path)
    _registrar(version=1, directorio=tmp_path)
    _registrar(version=3, directorio=tmp_path)

    assert [
        entrada["version"] for entrada in versiones.leer_versiones(ID_UNO, directorio=tmp_path)
    ] == [1, 2, 3]


def test_leer_versiones_sin_archivo_devuelve_lista_vacia(tmp_path):
    """S5: una solicitud sin historial no es un error."""
    assert versiones.leer_versiones(ID_UNO, directorio=tmp_path) == []


def test_registrar_una_version_existente_falla_y_no_sobrescribe(tmp_path):
    """S4/S15: 0 versiones anteriores perdidas o sobrescritas."""
    original = _registrar(version=1, directorio=tmp_path)

    with pytest.raises(versiones.ErrorVersiones):
        _registrar(version=1, programa=_programa(width=1, depth=1, thick=1), directorio=tmp_path)

    assert versiones.leer_versiones(ID_UNO, directorio=tmp_path) == [original]


def test_nueva_version_empieza_en_uno_y_sigue_el_maximo():
    """S4: la próxima versión es max+1, o 1 si el historial está vacío."""
    assert versiones.nueva_version([]) == 1
    assert versiones.nueva_version([{"version": 1}]) == 2
    assert versiones.nueva_version([{"version": 1}, {"version": 3}]) == 4


def test_ultima_version_devuelve_la_mas_alta(tmp_path):
    """S5: la versión vigente es la de número más alto; sin historial es None."""
    assert versiones.ultima_version(ID_UNO, directorio=tmp_path) is None

    _registrar(directorio=tmp_path)
    _registrar(directorio=tmp_path)
    tercera = _registrar(directorio=tmp_path)

    assert versiones.ultima_version(ID_UNO, directorio=tmp_path) == tercera


def test_registrar_una_declinacion_guarda_su_causa(tmp_path):
    """S6: la versión declinada registrada lleva la causa etiquetada."""
    entrada = _registrar(causa="dimension_incoherente", directorio=tmp_path)

    assert entrada["causa"] == "dimension_incoherente"


@pytest.mark.parametrize(
    "solicitud_id",
    ["../x", "a/b", "no-uuid", "", "   ", ID_UNO.upper(), ID_UNO + "0"],
    ids=["punto-punto", "barra", "texto", "vacio", "espacios", "mayusculas", "largo"],
)
def test_un_id_que_no_es_uuid_se_rechaza(tmp_path, solicitud_id):
    """S10: el índice no puede salir de su directorio."""
    with pytest.raises(versiones.ErrorVersiones):
        versiones.registrar_version(
            solicitud_id,
            usuario="ana",
            programa=PROGRAMA,
            artefactos=[],
            prompt="editor-v1",
            prompt_hash="a" * 64,
            directorio=tmp_path,
        )
    with pytest.raises(versiones.ErrorVersiones):
        versiones.leer_versiones(solicitud_id, directorio=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_el_id_con_guiones_es_el_mismo_historial(tmp_path):
    """S10: la forma canónica del id es un solo fragmento de nombre de archivo."""
    assert versiones.validar_solicitud_id(ID_GUIONES) == ID_UNO
    assert versiones.validar_solicitud_id(ID_UNO) == ID_UNO

    _registrar(ID_GUIONES, directorio=tmp_path)

    assert (tmp_path / f"{ID_UNO}.json").exists()
    assert len(versiones.leer_versiones(ID_UNO, directorio=tmp_path)) == 1


def test_un_indice_corrupto_es_error_versiones(tmp_path):
    """S5: un índice ilegible no se confunde con un historial vacío."""
    (tmp_path / f"{ID_UNO}.json").write_text("{no es json", encoding="utf-8")

    with pytest.raises(versiones.ErrorVersiones):
        versiones.leer_versiones(ID_UNO, directorio=tmp_path)
    with pytest.raises(versiones.ErrorVersiones):
        _registrar(directorio=tmp_path)


@pytest.mark.parametrize("contenido", ['{"version": 1}', "[1, 2]"], ids=["objeto", "numeros"])
def test_un_indice_que_no_es_lista_de_objetos_es_error(tmp_path, contenido):
    """S5: el índice es siempre una lista de objetos."""
    (tmp_path / f"{ID_UNO}.json").write_text(contenido, encoding="utf-8")

    with pytest.raises(versiones.ErrorVersiones):
        versiones.leer_versiones(ID_UNO, directorio=tmp_path)


def test_dos_solicitudes_nunca_comparten_estado(tmp_path):
    """S10: el historial es por solicitud."""
    _registrar(ID_UNO, directorio=tmp_path)
    _registrar(ID_DOS, programa=_programa(width=1, depth=1, thick=1), directorio=tmp_path)

    assert [
        entrada["version"] for entrada in versiones.leer_versiones(ID_UNO, directorio=tmp_path)
    ] == [1]
    assert [
        entrada["version"] for entrada in versiones.leer_versiones(ID_DOS, directorio=tmp_path)
    ] == [1]
    assert versiones.leer_versiones(ID_DOS, directorio=tmp_path)[0]["programa"] == _programa(
        width=1, depth=1, thick=1
    )


def test_la_variable_de_entorno_cambia_el_directorio(tmp_path, monkeypatch):
    """S10: `M2_VERSIONES_DIR` desvía el almacén sin tocar `data/`."""
    monkeypatch.delenv(versiones.VARIABLE_ENTORNO, raising=False)
    assert versiones.VARIABLE_ENTORNO == "M2_VERSIONES_DIR"
    assert versiones.ruta_versiones() == versiones.RUTA_VERSIONES
    assert versiones.RUTA_VERSIONES.parts[:2] == ("data", "versiones")

    destino = tmp_path / "versiones"
    monkeypatch.setenv(versiones.VARIABLE_ENTORNO, str(destino))
    assert versiones.ruta_versiones() == destino

    entrada = versiones.registrar_version(
        ID_UNO,
        usuario="ana",
        programa=PROGRAMA,
        artefactos=[],
        prompt="editor-v1",
        prompt_hash="a" * 64,
    )

    assert entrada["version"] == 1
    assert (destino / f"{ID_UNO}.json").exists()
    assert versiones.leer_versiones(ID_UNO) == [entrada]
