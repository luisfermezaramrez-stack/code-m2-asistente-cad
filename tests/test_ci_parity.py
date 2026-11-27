"""Paridad de verificación entre GitHub Actions y el pipeline de GitLab.

GitHub es la fuente de verdad y la puerta de integración; el pipeline de GitLab
deja evidencia verificable sobre el espejo. Esta prueba vigila las dos cosas que
pueden romperse en silencio: que las herramientas fijadas coincidan (uv, Python,
banderas de compilación) y que GitLab no se convierta en una segunda puerta de
integración. Se lee el YAML como texto a propósito: no hace falta un parser para
comprobar estas invariantes y evita sumar una dependencia solo para la prueba.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
GITLAB = RAIZ / ".gitlab-ci.yml"
GITHUB = RAIZ / ".github" / "workflows" / "ci.yml"
DOCKERFILE = RAIZ / "Dockerfile"
MAKEFILE = RAIZ / "Makefile"


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def _dependencias(nombre: str, makefile: str) -> list[str]:
    """Dependencias declaradas en la primera regla `nombre:` del Makefile."""
    for linea in makefile.splitlines():
        if linea.startswith(f"{nombre}:"):
            return linea.split(":", 1)[1].split()
    return []


def _job_gitlab(nombre: str) -> str:
    """Bloque YAML de un job de primer nivel (hasta la siguiente clave top-level)."""
    bloque: list[str] = []
    dentro = False
    for linea in _texto(GITLAB).splitlines():
        if linea.startswith(f"{nombre}:"):
            dentro = True
        elif dentro and linea and not linea.startswith((" ", "#")):
            break
        if dentro:
            bloque.append(linea)
    return "\n".join(bloque)


def test_uv_esta_fijado_igual_en_los_tres_lados():
    """Una sola versión de uv en GitHub, GitLab y el Dockerfile."""
    assert 'UV_VERSION: "0.13.5"' in _texto(GITLAB)
    assert 'version: "0.13.5"' in _texto(GITHUB)
    assert "ghcr.io/astral-sh/uv:0.13.5" in _texto(DOCKERFILE)


def test_python_sale_de_python_version_y_el_pipeline_lo_repite_igual():
    """`.python-version` es la única fuente de verdad (CONSTITUTION.md)."""
    version = (RAIZ / ".python-version").read_text(encoding="utf-8").strip()

    assert version, ".python-version no puede estar vacío"
    assert 'python-version-file: ".python-version"' in _texto(GITHUB)
    assert 'uv python install "$(cat .python-version)"' in _texto(GITLAB)
    # El tag de la imagen no puede leer un archivo: el valor repetido tiene que
    # seguir siendo el mismo, y la imagen tiene que armarse con las variables.
    assert f'PYTHON_VERSION: "{version}"' in _texto(GITLAB)
    assert "ghcr.io/astral-sh/uv:$UV_VERSION-python$PYTHON_VERSION-$BASE_LAYER" in _texto(GITLAB)


def test_los_sdists_se_compilan_en_c17_en_los_dos_lados():
    """python-solvespace y su mimalloc no compilan en C23."""
    assert 'CFLAGS: "-std=gnu17"' in _texto(GITLAB)
    assert 'CFLAGS: "-std=gnu17"' in _texto(GITHUB)


def test_los_dos_pipelines_preparan_el_kernel_vendoreado_y_el_frontend():
    """Sin el vendor de constraint-kit, `uv sync` falla; sin lockfile, no hay build."""
    for texto in (_texto(GITHUB), _texto(GITLAB)):
        assert "bash scripts/vendor-constraint-kit.sh" in texto
        assert "uv sync --locked --dev" in texto
    assert "make frontend-install" in _texto(GITHUB)
    assert "make frontend-install" in _texto(GITLAB)


def test_cada_pipeline_corre_la_verificacion_que_declara():
    """GitHub corre la verificación completa; GitLab la del espejo."""
    assert "make check" in _texto(GITHUB)
    assert "make test" in _texto(GITLAB)


def test_el_pipeline_de_gitlab_no_abre_segunda_puerta_de_integracion():
    gitlab = _texto(GITLAB)

    # Sólo push a la rama por defecto, lanzamiento manual o pipeline programado.
    assert "$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH" in gitlab
    assert "merge_request_event" not in gitlab


def test_el_lint_del_espejo_usa_el_makefile_y_no_recorre_todo_el_arbol():
    """`ruff check .` recorre `.agents/`, con plantillas que no son TOML válido."""
    gitlab = _texto(GITLAB)
    # El comentario que explica la trampa nombra el comando: se mira sólo lo que
    # se ejecuta, no las líneas de comentario.
    ejecutado = [linea for linea in gitlab.splitlines() if not linea.lstrip().startswith("#")]

    assert "make lint" in gitlab
    assert not [linea for linea in ejecutado if "ruff check ." in linea]


def test_los_dos_pipelines_generan_la_clave_efimera_de_descargas():
    """HU-36: 44 pruebas de descargas exigen M2_DOWNLOAD_SECRET en cada corrida."""
    assert "M2_DOWNLOAD_SECRET" in _texto(GITHUB)
    assert "M2_DOWNLOAD_SECRET" in _texto(GITLAB)


def test_el_chequeo_de_prompts_entra_en_check_y_en_el_job_lint():
    """HU-33/AC2/RF-5: el mismo chequeo corre en los dos pipelines.

    GitHub lo ejecuta dentro de `make check`; el espejo, dentro del job `lint`.
    Así un cambio de prompt sin subir su versión bloquea las dos puertas.
    """
    makefile = _texto(MAKEFILE)

    assert "prompts-check" in _dependencias("check", makefile)
    assert "prompts-check:" in makefile
    # El objetivo ejecuta el verificador offline (sin red, sin entorno del proyecto).
    cuerpo = next(
        linea
        for linea in makefile.split("prompts-check:", 1)[1].splitlines()
        if "scripts/verify_prompts.py" in linea
    )
    assert "uv run --no-project python -B scripts/verify_prompts.py" in cuerpo

    lint = _job_gitlab("lint")
    assert "uv run --no-sync make prompts-check" in lint
    # El job `lint` del espejo cubre entonces AC2 igual que `make check` en GitHub.
