"""Paridad de verificación entre GitHub Actions y el pipeline de GitLab.

GitHub es la fuente de verdad y la puerta de integración; el pipeline de GitLab
valida cada rama replicada y, sólo desde la rama por defecto, publica la imagen y
la despliega. Esta prueba vigila lo que puede romperse en silencio: que las
herramientas fijadas coincidan (uv, Python, banderas de compilación) y que ninguna
otra rama publique ni despliegue. Se lee el YAML como texto a propósito: no hace
falta un parser para comprobar estas invariantes y evita sumar una dependencia solo
para la prueba.
"""

import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
GITLAB = RAIZ / ".gitlab-ci.yml"
GITHUB = RAIZ / ".github" / "workflows" / "ci.yml"
SEGURIDAD = RAIZ / ".github" / "workflows" / "seguridad.yml"
MODULO_SEGURIDAD = RAIZ / "src" / "m2_cad" / "seguridad_ci.py"
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


def test_el_pipeline_de_gitlab_valida_cada_push_y_solo_main_publica_y_despliega():
    """Cada rama replicada se valida; sólo la rama por defecto publica y despliega."""
    workflow = _job_gitlab("workflow")

    assert '$CI_PIPELINE_SOURCE == "push"' in workflow
    assert "merge_request_event" not in _texto(GITLAB)
    for job in ("build_image", "deploy"):
        assert "$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH" in _job_gitlab(job), job
    # Sin droplet configurado el deploy no se agrega, en vez de fallar en rojo.
    assert "$DO_HOST" in _job_gitlab("deploy").split("rules:", 1)[1].split("\n  cache:")[0]


def test_run_pipeline_desde_la_web_puede_volver_a_desplegar():
    """Tras cambiar una variable en GitLab, "Run pipeline" crea un pipeline con deploy.

    Las reglas de los jobs se evalúan al crear el pipeline: reintentar uno viejo no
    agrega el deploy, así que sin esta regla haría falta un push nuevo a `main`.
    """
    workflow = _job_gitlab("workflow")

    assert '$CI_PIPELINE_SOURCE == "web"' in workflow
    assert '$CI_PIPELINE_SOURCE == "push"' in workflow


def test_el_deploy_no_depende_del_salto_final_de_la_clave_ssh():
    """GitLab escribe la variable File tal cual: sin salto final, ssh no carga la clave."""
    deploy = _job_gitlab("deploy")
    ejecutado = "\n".join(
        linea for linea in deploy.splitlines() if not linea.lstrip().startswith("#")
    )

    assert 'printf \'%s\\n\' "$(cat "$SSH_PRIVATE_KEY")" > "$DEPLOY_KEY"' in ejecutado
    assert "-i $DEPLOY_KEY" in ejecutado
    assert "-i $SSH_PRIVATE_KEY" not in ejecutado


def test_la_imagen_se_verifica_sana_antes_de_publicarse():
    """El smoke espera el HEALTHCHECK de `/v1/health` y la SPA antes del push."""
    build = _job_gitlab("build_image")
    ejecutado = "\n".join(
        linea for linea in build.splitlines() if not linea.lstrip().startswith("#")
    )

    assert "/v1/health" in ejecutado
    assert ejecutado.index("healthy") < ejecutado.index("docker push")
    assert "--target" not in ejecutado, "el Dockerfile no declara stages con nombre para la API"


def test_el_deploy_levanta_api_y_worker_sin_exponer_secretos():
    """HU-45: la API encola y el worker procesa; los secretos viajan en un env-file."""
    deploy = _job_gitlab("deploy")
    ejecutado = "\n".join(
        linea for linea in deploy.splitlines() if not linea.lstrip().startswith("#")
    )

    assert "--env-file" in ejecutado
    assert "m2_cad.worker" in ejecutado
    assert "/v1/health" in ejecutado
    for secreto in ("DEEPSEEK_API_KEY", "M2_AUTH_SECRET", "M2_AUTH_USERS", "M2_DOWNLOAD_SECRET"):
        assert f"-e {secreto}" not in ejecutado, f"{secreto} quedaría en la línea de comandos"
    assert "resource_group: production" in deploy
    # Un push nuevo no puede cancelar el deploy entre `docker rm -f` y el arranque.
    assert "interruptible: false" in deploy


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


def test_la_tabla_de_materiales_entra_en_check_y_en_el_espejo():
    """HU-48/RF-3: la tabla de precios se valida en las dos puertas, sin red.

    Un precio o una densidad mal declarados no pueden publicarse sin que falle CI, y la
    validación tiene que servir sin instalar el proyecto (solo biblioteca estándar).
    """
    makefile = _texto(MAKEFILE)

    assert "materiales-check" in _dependencias("check", makefile)
    assert "materiales-check:" in makefile
    cuerpo = next(
        linea
        for linea in makefile.split("materiales-check:", 1)[1].splitlines()
        if "scripts/verify_materiales.py" in linea
    )
    assert "uv run --no-project python -B scripts/verify_materiales.py" in cuerpo
    assert "uv run --no-sync make materiales-check" in _job_gitlab("lint")
    # La tabla es un artefacto versionado del repositorio, no configuración local.
    assert (RAIZ / "data" / "materiales.toml").is_file()


def test_la_configuracion_cloud_entra_en_check_y_en_el_espejo():
    """HU-47/RNF-3: la misma validación sin red corre en las dos puertas."""
    makefile = _texto(MAKEFILE)
    lint = _job_gitlab("lint")

    assert "cloud-config-check" in _dependencias("check", makefile)
    assert "cloud-config-check:" in makefile
    assert "uv run --no-sync make cloud-config-check" in lint
    # El job `lint` del espejo cubre entonces AC2 igual que `make check` en GitHub.


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


def test_los_dos_pipelines_corren_los_e2e_con_un_solo_navegador():
    """HU-41 (SPEC-042 RF-5, RNF-1): misma suite E2E y mismo artefacto de fallo.

    Los E2E no necesitan kernel CAD, API key ni GPU: solo Node y Chromium, por eso
    viven en un job propio y no dentro de `make check`. El job de GitHub publica
    captura y traza cuando falla (AC2); el del espejo deja la misma evidencia.
    """
    github = _texto(GITHUB)
    gitlab = _texto(GITLAB)

    for texto in (github, gitlab):
        assert "playwright install --with-deps chromium" in texto
        assert "frontend/test-results/" in texto
        assert "frontend/playwright-report/" in texto
    # Cada puerta invoca la suite con su propio lenguaje: make en GitHub, npm en GitLab.
    assert "make e2e" in github
    assert "npm --prefix frontend run e2e" in gitlab
    # AC2: en GitHub los artefactos salen solo cuando el job falla.
    assert "actions/upload-artifact@" in github
    assert "if: failure()" in github
    # El objetivo nunca prueba un build viejo: la suite siempre parte de `frontend-build`.
    assert "frontend-build" in _dependencias("e2e", _texto(MAKEFILE))
