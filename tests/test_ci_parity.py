"""Paridad de verificación entre GitHub Actions y el pipeline de GitLab.

GitHub es la fuente de verdad y la puerta de integración; el pipeline de GitLab
deja evidencia verificable sobre el espejo. Esta prueba vigila las dos cosas que
pueden romperse en silencio: que las herramientas fijadas coincidan (uv, Python,
banderas de compilación) y que GitLab no se convierta en una segunda puerta de
integración. Se lee el YAML como texto a propósito: no hace falta un parser para
comprobar estas invariantes y evita sumar una dependencia solo para la prueba.
"""

import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
GITLAB = RAIZ / ".gitlab-ci.yml"
GITHUB = RAIZ / ".github" / "workflows" / "ci.yml"
SEGURIDAD = RAIZ / ".github" / "workflows" / "seguridad.yml"
MODULO_SEGURIDAD = RAIZ / "src" / "m2_cad" / "seguridad_ci.py"
DOCKERFILE = RAIZ / "Dockerfile"


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


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


def test_los_dos_pipelines_corren_el_mismo_escaneo_de_seguridad():
    """HU-28 (S1, S2, S7): un solo comando por escáner, igual en GitHub y GitLab."""
    github = _texto(SEGURIDAD)
    gitlab = _texto(GITLAB)

    for texto in (github, gitlab):
        assert "make security-secretos" in texto
        assert "make security-dependencias" in texto


def test_las_herramientas_de_seguridad_estan_fijadas_en_los_tres_lados():
    """HU-28 (S6, RNF-2): gitleaks y pip-audit no se resuelven en cada corrida."""
    for ruta in (SEGURIDAD, GITLAB, MODULO_SEGURIDAD):
        texto = _texto(ruta)

        assert "8.30.1" in texto, f"{ruta} no fija gitleaks 8.30.1"
        assert "pip-audit==2.10.1" in texto, f"{ruta} no fija pip-audit 2.10.1"


def test_ningun_pipeline_de_seguridad_instala_con_pip():
    """HU-28 (S7, RNF-3): la gestión de Python pasa por uv, nunca por pip."""
    for ruta in (SEGURIDAD, GITLAB):
        assert "pip install" not in _texto(ruta), f"{ruta} usa pip"


def test_los_archivos_de_excepciones_existen_y_son_listas_de_tablas():
    """HU-28 (S4, S10): el esquema viaja documentado; la política la valida el job."""
    for nombre in ("excepciones-secretos.toml", "excepciones-dependencias.toml"):
        ruta = RAIZ / "security" / nombre

        assert ruta.is_file(), f"falta {ruta}"
        datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
        assert isinstance(datos.get("excepciones", []), list), f"{ruta} no usa [[excepciones]]"


def test_cada_escaneo_valida_la_politica_de_excepciones_antes_de_correr():
    """HU-28 (S12): una excepción incompleta no puede desbloquear un hallazgo en CI."""
    makefile = _texto(RAIZ / "Makefile").splitlines()
    for objetivo in ("security-secretos", "security-dependencias"):
        linea = next(linea for linea in makefile if linea.startswith(f"{objetivo}:"))

        prerequisitos = linea.split("##")[0]
        assert "security-excepciones-validar" in prerequisitos, f"{objetivo} no valida"


def test_el_job_de_secretos_de_gitlab_instala_git():
    """HU-28 (S2): `gitleaks git` necesita git; la imagen de uv no lo trae."""
    bloque = _texto(GITLAB).split("\nsecretos:")[1].split("\ndependencias:")[0]

    instalaciones = [linea for linea in bloque.splitlines() if "apt-get install" in linea]
    assert instalaciones, "el job de secretos no instala sus herramientas"
    assert any(" git" in linea.split("--no-install-recommends")[-1] for linea in instalaciones)
