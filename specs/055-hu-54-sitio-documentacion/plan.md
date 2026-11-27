# Plan de implementación · HU-54 (SPEC-055)

## Decisión de arquitectura

No se reescribe la documentación ni se duplica su contenido. Se publica el Markdown que ya
vive en `README.md`, `CONSTITUTION.md`, `docs/` y `specs/` con MkDocs 1.6.1, fijado en
`uv.lock` y gestionado con `uv` (RNF-1). El tema es el incluido en MkDocs: sin dependencias
de terceros, sin red durante el build y sin API key ni GPU (RNF-2).

1. **Fuente única.** MkDocs exige que `docs_dir` sea hijo del directorio de configuración,
   por lo que `scripts/build_docs_site.py` genera `docs-build/` antes de cada build: copia
   los Markdown de la raíz, `docs/` y `specs/` manteniendo sus rutas y copia sólo los
   recursos relativos que esos Markdown enlazan. El staging es gitignored y se regenera
   desde cero; ningún documento se duplica en el repositorio. Los enlaces relativos
   (`../CONSTITUTION.md`, `../README.md`, `specs/...`) siguen resolviéndose igual.
2. **Exclusiones y enlaces rotos.** El staging incluye únicamente documentación y los
   archivos punto enlazados (`.python-version`, `.env.example`, `.gitignore`,
   `.github/dependabot.yml`, `.opencode/rules/tgrep.md`). Los 30 enlaces a STEP no
   versionados dentro de `docs/hu07/**` se convierten en código en el staging, porque el
   binario no existe y publicarlo no es parte de esta HU; cualquier otro destino ausente
   sigue fallando el build. Nav omitida, anclas históricas y enlaces a directorios se
   ignoran (`ignore`) para no enmascarar enlaces rotos reales.
3. **Navegación.** `nav` explícito con cinco secciones: Uso, Arquitectura, Operación,
   Especificaciones y Decisiones. El runbook de SPEC-030 se enlaza directamente desde
   Operación, sin copiar su texto (AC3). Las páginas no listadas en `nav` siguen
   accesibles por enlace y no generan avisos (`omitted_files: ignore`).
4. **Enlaces rotos.** `validation.links.not_found: warn` y `mkdocs build --strict` hacen
   fallar el build ante cualquier destino inexistente (RF-4). `anchors` y
   `unrecognized_links` quedan en `ignore` para no convertir TOCs históricas de GitHub en
   falsos positivos; los enlaces a directorios se revisan cuando son parte de la nav.
5. **Interfaz de comandos.** `make docs-stage` ejecuta el generador;
   `make docs-build` encadena staging y `uv run --locked mkdocs build --strict`;
   `make docs-serve` levanta la vista previa. `docs-build` entra en `make check`, de modo
   que la puerta existente verifica AC1.
6. **Publicación.** `.github/workflows/docs-pages.yml` se dispara con `push` a `main`
   cuando cambia documentación o su configuración, construye con el mismo `make docs-build`
   y despliega con las actions oficiales de GitHub Pages. La publicación real requiere que
   `main` tenga el workflow y que Pages esté configurado con fuente *GitHub Actions*; un PR
   no puede publicar por sí solo (AC2).

### Componentes

- `mkdocs.yml`: fuente del sitio, navegación, validación estricta y reinyección de archivos punto.
- `scripts/build_docs_site.py`: staging reproducible desde los Markdown versionados.
- `pyproject.toml` y `uv.lock`: `mkdocs==1.6.1` en el grupo `dev`, añadido con `uv`.
- `Makefile`: targets `docs-stage`, `docs-build` y `docs-serve`; `docs-build` dentro de `check`.
- `.gitignore`: ignora `docs-build/`, `.site/` y `site/`.
- `.github/workflows/docs-pages.yml`: build y despliegue a Pages tras fusión en `main`.
- `CONSTITUTION.md`: registra la decisión y el comando en la tabla de calidad.
- `specs/055-hu-54-sitio-documentacion/`: `plan.md`, `tasks.md` y `evidence.md`.
- `tests/test_docs_sitio.py`: comprueba que la nav incluye el runbook, que el build es
  estricto y que el workflow publica desde `main`.

## Verificación

1. `make docs-build` sin errores ni avisos de enlaces rotos.
2. Comprobar en el HTML generado que `docs/runbook-operativo.md` está en la navegación y
   que su texto no se duplicó.
3. `make check` y auditoría no destructiva de `jan-project-standard`.
4. PR a `main` con `Closes #114`; el merge y la configuración de Pages quedan fuera del PR.
