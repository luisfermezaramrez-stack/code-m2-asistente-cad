"""Pruebas de SPEC-029 (HU-28): escaneo de secretos y dependencias en CI.

Todo corre sin red, sin el binario de gitleaks y sin pip-audit: los reportes se
leen de `tests/fixtures/seguridad/` con la forma real de cada herramienta. El
patrón es AAA (Arrange · Act · Assert) y nunca se aprueba una excepción real.
"""

import json
import tomllib
from datetime import date, timedelta
from pathlib import Path

import pytest

from m2_cad import seguridad_ci

RAIZ = Path(__file__).resolve().parents[1]
FIXTURES = RAIZ / "tests" / "fixtures" / "seguridad"
HOY = date(2026, 11, 27)


def _json(nombre: str):
    return json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))


def _clasificar_dependencias(severidades=None, excepciones=()):
    auditoria = _json("pip-audit-hallazgo.json")
    return seguridad_ci.clasificar_dependencias(
        auditoria,
        severidades if severidades is not None else {"PYSEC-2026-1475": "alta"},
        list(excepciones),
        HOY,
    )


def _excepcion_dependencia(revision: str, **extra) -> dict:
    entrada = {
        "advisory": "PYSEC-2026-1475",
        "paquete": "jinja2",
        "justificacion": "El paquete solo se usa en pruebas internas sin plantillas ajenas.",
        "aprobado_por": "Responsable de la entrega",
        "revision": revision,
    }
    entrada.update(extra)
    return entrada


def _excepcion_secreto(revision: str, **extra) -> dict:
    entrada = {
        "archivo": "tests/fixtures/seguridad/secreto-falso.env",
        "linea": 2,
        "regla": "generic-api-key",
        "justificacion": "El valor es una credencial falsa usada por la suite de pruebas.",
        "aprobado_por": "Responsable de la entrega",
        "revision": revision,
    }
    entrada.update(extra)
    return entrada


# ---------------------------------------------------------------------------
# AC1 (RF-2, RF-3, S8): el reporte de secretos señala archivo, línea y pasos.
# ---------------------------------------------------------------------------


def test_ac1_mensaje_secretos_senala_archivo_linea_regla_y_los_tres_pasos():
    hallazgos = _json("gitleaks-hallazgo.json")

    mensaje = seguridad_ci.mensaje_secretos(hallazgos, hoy=HOY)

    assert "tests/fixtures/seguridad/secreto-falso.env:2" in mensaje
    assert "generic-api-key" in mensaje
    assert "rotar la clave en el proveedor" in mensaje
    assert "retirarla del historial (por ejemplo con git filter-repo)" in mensaje
    assert "declarar una excepción justificada en security/excepciones-secretos.toml" in mensaje
    assert "RESULTADO: 1 hallazgo bloqueante" in mensaje


def test_ac1_mensaje_secretos_sin_hallazgos_informa_paso():
    mensaje = seguridad_ci.mensaje_secretos([], hoy=HOY)

    assert "RESULTADO: escaneo de secretos superado" in mensaje


def test_ac3_excepcion_de_secreto_vigente_desbloquea_y_queda_visible():
    hallazgos = _json("gitleaks-hallazgo.json")

    mensaje = seguridad_ci.mensaje_secretos(
        hallazgos, excepciones=[_excepcion_secreto(HOY.isoformat())], hoy=HOY
    )

    assert "tests/fixtures/seguridad/secreto-falso.env:2" in mensaje
    assert "excepción vigente" in mensaje
    assert "RESULTADO: escaneo de secretos superado" in mensaje


def test_ac3_excepcion_de_secreto_vencida_vuelve_a_bloquear():
    hallazgos = _json("gitleaks-hallazgo.json")

    mensaje = seguridad_ci.mensaje_secretos(
        hallazgos, excepciones=[_excepcion_secreto((HOY - timedelta(days=1)).isoformat())], hoy=HOY
    )

    assert "RESULTADO: 1 hallazgo bloqueante" in mensaje
    assert "excepción vencida" in mensaje


# ---------------------------------------------------------------------------
# AC2 (RF-1, RF-3, S9): el reporte de dependencias nombra paquete, CVE,
# versión corregida y el comando exacto para actualizar.
# ---------------------------------------------------------------------------


def test_ac2_mensaje_dependencias_nombra_paquete_cve_correccion_y_comando():
    hallazgos = _clasificar_dependencias()

    mensaje = seguridad_ci.mensaje_dependencias(hallazgos, paquetes_auditados=1)

    assert len(hallazgos) == 1
    assert hallazgos[0].paquete == "jinja2"
    assert hallazgos[0].cve == "CVE-2024-56326"
    assert hallazgos[0].bloqueante is True
    for fragmento in (
        "jinja2",
        "2.11.2",
        "CVE-2024-56326",
        "severidad alta",
        "3.1.5",
        "uv lock --upgrade-package jinja2",
        'uv add "jinja2>=3.1.5"',
        "security/excepciones-dependencias.toml",
    ):
        assert fragmento in mensaje
    assert "RESULTADO: 1 hallazgo bloqueante" in mensaje


def test_ac2_hallazgo_sin_correccion_lo_declara_y_no_inventa_version():
    auditoria = {
        "dependencies": [
            {
                "name": "diskcache",
                "version": "5.6.3",
                "vulns": [
                    {"id": "CVE-2025-69872", "fix_versions": [], "aliases": ["CVE-2025-69872"]}
                ],
            }
        ],
        "fixes": [],
    }

    hallazgos = seguridad_ci.clasificar_dependencias(
        auditoria, {"CVE-2025-69872": "desconocida"}, [], HOY
    )
    mensaje = seguridad_ci.mensaje_dependencias(hallazgos, paquetes_auditados=1)

    assert hallazgos[0].correccion is None
    assert hallazgos[0].bloqueante is True
    assert "sin versión corregida" in mensaje
    assert "uv lock --upgrade-package diskcache" in mensaje
    assert "uv add" not in mensaje


def test_hallazgo_informacional_no_bloquea_pero_se_informa():
    auditoria = {
        "dependencies": [
            {
                "name": "paquete-medio",
                "version": "1.0.0",
                "vulns": [
                    {"id": "PYSEC-2026-0001", "fix_versions": [], "aliases": ["CVE-2026-0001"]}
                ],
            }
        ],
        "fixes": [],
    }

    hallazgos = seguridad_ci.clasificar_dependencias(
        auditoria, {"PYSEC-2026-0001": "media"}, [], HOY
    )
    mensaje = seguridad_ci.mensaje_dependencias(hallazgos, paquetes_auditados=1)

    assert hallazgos[0].bloqueante is False
    assert "informacional" in mensaje
    assert "paquete-medio" in mensaje
    assert "RESULTADO: auditoría de dependencias superada: 1 paquete auditado" in mensaje


def test_las_dependencias_no_auditables_se_informan_sin_bloquear():
    mensaje = seguridad_ci.mensaje_dependencias(
        [], paquetes_auditados=1, no_auditables=["constraint-kit (file:./vendor/constraint-kit)"]
    )

    assert "constraint-kit (file:./vendor/constraint-kit)" in mensaje
    assert "no auditable" in mensaje
    assert "RESULTADO: auditoría de dependencias superada" in mensaje


def test_un_advisory_repetido_es_un_solo_hallazgo():
    advisory = {"id": "PYSEC-2026-1475", "fix_versions": ["3.1.5"], "aliases": ["CVE-2024-56326"]}
    auditoria = {
        "dependencies": [
            {"name": "jinja2", "version": "2.11.2", "vulns": [dict(advisory), dict(advisory)]}
        ],
        "fixes": [],
    }

    hallazgos = seguridad_ci.clasificar_dependencias(
        auditoria, {"PYSEC-2026-1475": "alta"}, [], HOY
    )

    assert len(hallazgos) == 1


# ---------------------------------------------------------------------------
# AC3 (RF-4, S10): excepciones vigentes desbloquean y quedan visibles; las
# vencidas vuelven a bloquear.
# ---------------------------------------------------------------------------


def test_ac3_excepcion_vigente_desbloquea_pero_sigue_visible():
    hallazgos = _clasificar_dependencias(excepciones=[_excepcion_dependencia(HOY.isoformat())])

    mensaje = seguridad_ci.mensaje_dependencias(hallazgos, paquetes_auditados=1)

    assert hallazgos[0].bloqueante is False
    assert hallazgos[0].excepcion is not None
    assert hallazgos[0].excepcion_vencida is False
    # Visible: el mismo hallazgo, con su justificación y su fecha de revisión.
    assert "jinja2" in mensaje
    assert "CVE-2024-56326" in mensaje
    assert "excepción vigente" in mensaje
    assert HOY.isoformat() in mensaje
    assert "RESULTADO: auditoría de dependencias superada: 1 paquete auditado" in mensaje


def test_ac3_excepcion_vencida_bloquea_y_se_informa_vencida():
    ayer = (HOY - timedelta(days=1)).isoformat()

    hallazgos = _clasificar_dependencias(excepciones=[_excepcion_dependencia(ayer)])

    mensaje = seguridad_ci.mensaje_dependencias(hallazgos, paquetes_auditados=1)

    assert hallazgos[0].bloqueante is True
    assert hallazgos[0].excepcion_vencida is True
    assert "excepción vencida" in mensaje
    assert ayer in mensaje
    assert "RESULTADO: 1 hallazgo bloqueante" in mensaje


def test_la_excepcion_vigente_de_otro_advisory_no_desbloquea():
    hallazgos = _clasificar_dependencias(
        excepciones=[_excepcion_dependencia(HOY.isoformat(), advisory="CVE-2020-0000")]
    )

    assert hallazgos[0].bloqueante is True


def test_la_excepcion_por_cve_tambien_desbloquea():
    hallazgos = _clasificar_dependencias(
        excepciones=[_excepcion_dependencia(HOY.isoformat(), advisory="CVE-2024-56326")]
    )

    assert hallazgos[0].bloqueante is False


# ---------------------------------------------------------------------------
# RF-4 (S4): validación de la política de excepciones.
# ---------------------------------------------------------------------------


def test_validar_excepciones_acepta_una_entrada_completa_y_vigente():
    datos = {"excepciones": [_excepcion_dependencia(HOY.isoformat())]}

    errores = seguridad_ci.validar_excepciones(datos, "dependencias", HOY)

    assert errores == []


@pytest.mark.parametrize(
    "campo", ["justificacion", "aprobado_por", "revision", "advisory", "paquete"]
)
def test_validar_excepciones_exige_los_campos_obligatorios(campo):
    entrada = _excepcion_dependencia(HOY.isoformat())
    entrada.pop(campo)

    errores = seguridad_ci.validar_excepciones({"excepciones": [entrada]}, "dependencias", HOY)

    assert any(campo in error for error in errores)


@pytest.mark.parametrize(
    "campo", ["justificacion", "aprobado_por", "revision", "archivo", "linea", "regla"]
)
def test_validar_excepciones_de_secretos_exige_sus_campos(campo):
    entrada = _excepcion_secreto(HOY.isoformat())
    entrada.pop(campo)

    errores = seguridad_ci.validar_excepciones({"excepciones": [entrada]}, "secretos", HOY)

    assert any(campo in error for error in errores)


def test_validar_excepciones_rechaza_justificacion_corta_o_vacia():
    corta = _excepcion_dependencia(HOY.isoformat(), justificacion="porque sí")
    vacia = _excepcion_dependencia(HOY.isoformat(), justificacion="   ")

    errores = seguridad_ci.validar_excepciones({"excepciones": [corta, vacia]}, "dependencias", HOY)

    assert sum("justificacion" in error for error in errores) == 2


def test_validar_excepciones_rechaza_fecha_de_revision_vencida():
    datos = {"excepciones": [_excepcion_dependencia((HOY - timedelta(days=1)).isoformat())]}

    errores = seguridad_ci.validar_excepciones(datos, "dependencias", HOY)

    assert any("vencida" in error and "revision" in error for error in errores)


def test_validar_excepciones_rechaza_fecha_no_iso():
    datos = {"excepciones": [_excepcion_dependencia("31/12/2027")]}

    errores = seguridad_ci.validar_excepciones(datos, "dependencias", HOY)

    assert any("revision" in error for error in errores)


def test_validar_excepciones_rechaza_fecha_de_revision_mayor_a_180_dias():
    datos = {"excepciones": [_excepcion_dependencia((HOY + timedelta(days=181)).isoformat())]}

    errores = seguridad_ci.validar_excepciones(datos, "dependencias", HOY)

    assert any("180" in error for error in errores)


def test_validar_excepciones_rechaza_claves_desconocidas_y_entradas_no_tabla():
    datos = {"revisiones": [], "excepciones": ["texto suelto"]}

    errores = seguridad_ci.validar_excepciones(datos, "secretos", HOY)

    assert any("revisiones" in error for error in errores)
    assert any("tabla" in error for error in errores)


def test_validar_excepciones_sin_entradas_es_valido():
    assert seguridad_ci.validar_excepciones({}, "secretos", HOY) == []
    assert seguridad_ci.validar_excepciones({"excepciones": []}, "dependencias", HOY) == []


def _herramienta(ruta: Path) -> str:
    return "secretos" if "secretos" in ruta.name else "dependencias"


def test_los_archivos_de_excepciones_del_repositorio_no_tienen_entradas_aprobadas():
    for ruta in (
        seguridad_ci.RUTA_EXCEPCIONES_SECRETOS,
        seguridad_ci.RUTA_EXCEPCIONES_DEPENDENCIAS,
    ):
        datos = tomllib.loads((RAIZ / ruta).read_text(encoding="utf-8"))

        assert seguridad_ci.validar_excepciones(datos, _herramienta(ruta), HOY) == []
        assert seguridad_ci.cargar_excepciones(RAIZ / ruta) == []
        assert "excepciones" not in datos, f"{ruta} no debe tener excepciones aprobadas todavía"


def test_cargar_excepciones_devuelve_lista_vacia_sin_entradas(tmp_path):
    archivo = tmp_path / "excepciones-secretos.toml"
    archivo.write_text("# sin entradas\n", encoding="utf-8")

    assert seguridad_ci.cargar_excepciones(archivo) == []


def test_cargar_excepciones_lee_las_entradas_declaradas(tmp_path):
    archivo = tmp_path / "excepciones-dependencias.toml"
    archivo.write_text(
        '[[excepciones]]\nadvisory = "PYSEC-2026-1475"\npaquete = "jinja2"\n',
        encoding="utf-8",
    )

    entradas = seguridad_ci.cargar_excepciones(archivo)

    assert len(entradas) == 1
    assert entradas[0]["advisory"] == "PYSEC-2026-1475"


# ---------------------------------------------------------------------------
# Severidad: CVSS v3 y OSV (RF-3).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("vector", "esperado"),
    [
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8),
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H", 7.5),
        ("CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H", 7.8),
    ],
)
def test_severidad_cvss_v3_calcula_la_puntuacion_base(vector, esperado):
    assert seguridad_ci.severidad_cvss_v3(vector) == pytest.approx(esperado)


def test_severidad_cvss_v3_de_un_vector_local_y_complejo_es_baja():
    puntuacion = seguridad_ci.severidad_cvss_v3("CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N")

    assert puntuacion < 4.0


def test_severidad_cvss_v3_rechaza_un_vector_invalido():
    with pytest.raises(ValueError):
        seguridad_ci.severidad_cvss_v3("CVSS:3.1/AV:X")


def test_severidad_de_osv_usa_la_severidad_publicada():
    def severidad(valor: str) -> str:
        return seguridad_ci.severidad_de_osv({"database_specific": {"severity": valor}})

    assert severidad("HIGH") == "alta"
    assert severidad("CRITICAL") == "crítica"
    assert severidad("MODERATE") == "media"
    assert severidad("LOW") == "baja"


@pytest.mark.parametrize(
    ("vector", "esperado"),
    [
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "crítica"),
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H", "alta"),
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N", "media"),
        ("CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N", "baja"),
    ],
)
def test_severidad_de_osv_usa_el_vector_cvss_v3(vector, esperado):
    osv = {"severity": [{"type": "CVSS_V3", "score": vector}]}

    assert seguridad_ci.severidad_de_osv(osv) == esperado


def test_severidad_de_osv_solo_con_vector_v4_es_desconocida():
    osv = {
        "severity": [
            {
                "type": "CVSS_V4",
                "score": "CVSS:4.0/AV:L/AC:L/AT:P/PR:L/UI:P/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
            }
        ]
    }

    assert seguridad_ci.severidad_de_osv(osv) == "desconocida"


def test_severidad_de_osv_sin_datos_es_desconocida():
    assert seguridad_ci.severidad_de_osv({}) == "desconocida"


def test_las_herramientas_estan_fijadas_con_su_huella():
    assert seguridad_ci.VERSION_GITLEAKS == "8.30.1"
    assert seguridad_ci.VERSION_PIP_AUDIT == "2.10.1"
    assert seguridad_ci.URL_GITLEAKS_LINUX_X64.endswith("gitleaks_8.30.1_linux_x64.tar.gz")
    assert seguridad_ci.SHA256_GITLEAKS_LINUX_X64 == (
        "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
    )
