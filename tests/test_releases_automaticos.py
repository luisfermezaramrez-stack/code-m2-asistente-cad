"""HU-55: versión semántica, changelog y coherencia de release (SPEC-056)."""

from m2_cad.releases import (
    actualizar_changelog,
    analizar_commit,
    analizar_commits,
    es_convencional,
    generar_seccion,
    hay_versionamiento,
    leer_version_pyproject,
    normalizar_version,
    siguiente_version,
    sincronizar_version_pyproject,
    versiones_coinciden,
)


def test_ac1_solo_fixes_genera_parche_y_changelog_agrupado():
    commits = analizar_commits(
        [
            "fix(api): corregir el token de descarga",
            "fix(ui): conservar el historial tras recargar",
            "docs: aclarar el runbook operativo",
        ]
    )

    version = siguiente_version("1.0.1", commits)
    notas = generar_seccion(version, commits, fecha="2026-11-27")

    assert version == "1.0.2"
    assert "## [v1.0.2] - 2026-11-27" in notas
    assert "### Correcciones" in notas
    assert "### Documentación" in notas
    assert notas.index("### Correcciones") < notas.index("### Documentación")


def test_ac2_breaking_change_contrato_genera_mayor_y_destaca_incompatible():
    mensaje = (
        "feat(api)!: retirar el campo obsoleto de la respuesta\n\n"
        "BREAKING CHANGE: los clientes deben leer el campo nuevo de /v1"
    )
    commits = [analizar_commit(mensaje)]
    archivos = ["contracts/openapi-v1.json", "frontend/src/generated/api.ts"]

    version = siguiente_version("1.0.1", commits, archivos)
    notas = generar_seccion(version, commits, fecha="2026-11-27", archivos=archivos)

    assert commits[0].ruptura is True
    assert version == "2.0.0"
    assert "### Cambios incompatibles" in notas
    assert "BREAKING CHANGE" in notas
    assert "El contrato `/v1` cambia de forma incompatible (SPEC-032)." in notas


def test_ac3_etiqueta_y_pyproject_coinciden():
    contenido = '[project]\nname = "m2-cad"\nversion = "1.2.3"\n'

    assert normalizar_version("v1.2") == "1.2.0"
    assert leer_version_pyproject(contenido) == "1.2.3"
    assert versiones_coinciden("v1.2.3", contenido) is True
    assert versiones_coinciden("v1.2.4", contenido) is False


def test_cambios_sin_versionamiento_no_publican_release():
    commits = analizar_commits(["docs: corregir una coma", "chore: ordenar imports"])

    assert hay_versionamiento(commits) is False
    assert siguiente_version("1.0.1", commits) == "1.0.1"


def test_changelog_existente_no_duplica_la_nueva_seccion():
    previo = "# Changelog\n\n## [v1.0.1] - 2026-11-14\n\n### Documentación\n\n- anterior\n"
    seccion = "## [v1.0.2] - 2026-11-27\n\n### Correcciones\n\n- nuevo\n"

    resultado = actualizar_changelog(previo, seccion)

    assert resultado.count("## [v1.0.2]") == 1
    assert "## [v1.0.1]" in resultado
    assert resultado.index("## [v1.0.2]") < resultado.index("## [v1.0.1]")
    assert actualizar_changelog(resultado, seccion) == resultado


def test_sincronizar_version_pyproject_solo_toca_la_version():
    contenido = '[project]\nname = "m2-cad"\nversion = "0.1.0"\nreadme = "README.md"\n'

    resultado = sincronizar_version_pyproject(contenido, "v1.0.1")

    assert 'version = "1.0.1"' in resultado
    assert 'name = "m2-cad"' in resultado
    assert 'readme = "README.md"' in resultado


def test_titulo_no_convencional_se_detecta_antes_de_fusionar():
    assert es_convencional("feat(hu-55): publicar releases con changelog") is True
    assert es_convencional("chore(hu-55)!: cambiar el contrato /v1") is True
    assert es_convencional("Actualizar el contrato") is False
    assert es_convencional("feature: escribir mal el tipo") is False
