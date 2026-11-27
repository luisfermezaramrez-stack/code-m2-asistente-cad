"""SPEC-055 (HU-54): invariantes del sitio de documentación publicado.

Se lee la configuración como texto para no añadir un parser YAML sólo para probar
cadenas estables: lo que debe fallar es que desaparezca la nav del runbook, que el
build deje de ser estricto o que el workflow deje de publicar desde `main`.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "mkdocs.yml"
MAKEFILE = RAIZ / "Makefile"
WORKFLOW = RAIZ / ".github" / "workflows" / "docs-pages.yml"
GENERADOR = RAIZ / "scripts" / "build_docs_site.py"
RUNBOOK = RAIZ / "docs" / "runbook-operativo.md"


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def _dependencias(nombre: str, makefile: str) -> list[str]:
    for linea in makefile.splitlines():
        if linea.startswith(f"{nombre}:"):
            return linea.split(":", 1)[1].split("##")[0].split()
    return []


def test_el_runbook_esta_en_la_navegacion_y_su_fuente_existe():
    configuracion = _texto(CONFIG)

    assert RUNBOOK.is_file()
    assert "Runbook operativo: docs/runbook-operativo.md" in configuracion


def test_el_build_es_estricto_y_detecta_enlaces_rotos():
    configuracion = _texto(CONFIG)
    makefile = _texto(MAKEFILE)

    assert "docs_dir: docs-build" in configuracion
    assert "site_dir: .site" in configuracion
    assert "not_found: warn" in configuracion
    assert "mkdocs build --strict" in makefile
    assert "docs-build" in _dependencias("check", makefile)


def test_el_staging_sale_de_las_fuentes_versionadas_y_no_publica_step_inexistente():
    generador = _texto(GENERADOR)

    assert "docs-build" in generador
    assert 'RAIZ.rglob("*.md")' in generador
    assert "EVIDENCIA_HU07" in generador
    assert '.endswith(".step")' in generador


def test_el_lint_cubre_el_generador_del_sitio():
    makefile = _texto(MAKEFILE)

    assert "scripts/build_docs_site.py" in makefile
    assert "docs-stage" in _dependencias("docs-build", makefile)


def test_el_workflow_publica_el_sitio_desde_main():
    workflow = _texto(WORKFLOW)

    assert "branches: [main]" in workflow
    assert "workflow_dispatch:" in workflow
    assert "make docs-build" in workflow
    assert "path: .site" in workflow
    assert "actions/deploy-pages@v4" in workflow
