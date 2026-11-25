"""Paridad de verificación entre GitHub Actions y el pipeline de GitLab.

El pipeline de GitLab repite sobre el espejo la misma verificación que GitHub
Actions y no puede debilitarla sin que esta prueba falle. Se lee el YAML como
texto a propósito: no hace falta un parser para comprobar los pasos compartidos
y evita sumar una dependencia de desarrollo solo para estas pruebas.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
GITLAB = RAIZ / ".gitlab-ci.yml"
GITHUB = RAIZ / ".github" / "workflows" / "ci.yml"

# Los cinco pasos de `.github/workflows/ci.yml:38-56`, en orden de ejecución.
PASOS_COMPARTIDOS = (
    "bash scripts/vendor-constraint-kit.sh",
    "uv sync --locked --dev",
    "make frontend-install",
    "make check",
    "scripts/verify_hu15_deployment.py --simulate-model",
)


def test_gitlab_repite_los_pasos_de_github():
    gitlab = GITLAB.read_text(encoding="utf-8")
    github = GITHUB.read_text(encoding="utf-8")
    for paso in PASOS_COMPARTIDOS:
        assert paso in github, f"GitHub ya no ejecuta {paso!r}: revisar el pipeline de GitLab"
        assert paso in gitlab, f"GitLab no ejecuta {paso!r}"


def test_las_herramientas_fijadas_coinciden():
    gitlab = GITLAB.read_text(encoding="utf-8")
    github = GITHUB.read_text(encoding="utf-8")
    # La misma versión de uv en los dos pipelines y en el Dockerfile.
    assert 'UV_VERSION: "0.13.5"' in gitlab
    assert 'version: "0.13.5"' in github
    # python-solvespace se compila desde sdist en C17 en ambos lados.
    assert 'CFLAGS: "-std=gnu17"' in gitlab
    assert 'CFLAGS: "-std=gnu17"' in github


def test_python_sale_de_python_version_y_no_se_duplica():
    gitlab = GITLAB.read_text(encoding="utf-8")
    version = (RAIZ / ".python-version").read_text(encoding="utf-8").strip()
    assert version, ".python-version no puede estar vacío"
    # `.python-version` es la única fuente de verdad (CONSTITUTION.md:93).
    assert 'uv python install "$(cat .python-version)"' in gitlab
    assert "PYTHON_VERSION" not in gitlab
    assert 'python-version-file: ".python-version"' in (
        RAIZ / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")


def test_el_pipeline_no_abre_segunda_puerta_de_integracion():
    gitlab = GITLAB.read_text(encoding="utf-8")
    # Solo push a la rama por defecto; ningún pipeline de merge request ni de tag.
    assert "$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH" in gitlab
    assert "merge_request_event" not in gitlab
    assert "when: never" not in gitlab
