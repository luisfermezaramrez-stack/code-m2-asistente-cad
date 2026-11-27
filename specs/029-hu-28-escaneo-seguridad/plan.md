# SPEC-029 — HU-28 · Plan técnico

Issue: #88 · Rama: `feature/hu-28-escaneo-seguridad` · Destino PR: `main`.

## Alcance y diseño

Dos puertas nuevas en CI, una política de excepciones y un único lugar donde viven los
comandos (el `Makefile`, como ya exige la CONSTITUTION):

| Pieza | Qué hace |
|---|---|
| `src/m2_cad/seguridad_ci.py` | Lógica pura: clasifica la auditoría, arma los mensajes en español y valida las excepciones. Sin red, sin gitleaks ni pip-audit instalados al importarse. |
| `scripts/security_secretos.py` | Descarga el gitleaks **fijado**, verifica su sha256, lo corre sobre el historial y traduce el reporte JSON. |
| `scripts/security_dependencias.py` | Exporta `uv.lock` con `uv export`, audita con `pip-audit` **fijado** vía `uvx` y traduce el reporte JSON. |
| `scripts/security_excepciones.py` | Valida la política: justificación, aprobador y fecha de revisión vigente. |
| `security/` | `politica-excepciones.md`, `excepciones-secretos.toml`, `excepciones-dependencias.toml`. |
| `.github/workflows/seguridad.yml` | Jobs `secretos` y `dependencias` (RF-1, RF-2). |
| `.gitlab-ci.yml` | Los mismos dos jobs, en el stage `quality`, con los mismos comandos. |

- **Versiones exactas** (RNF-2): gitleaks `8.30.1` (asset y sha256 fijados en el script),
  pip-audit `2.10.1` (`uvx --from pip-audit==2.10.1`), uv `0.13.5` (ya fijado en los tres
  lados y vigilado por `tests/test_ci_parity.py`).
- **Todo lo de Python pasa por `uv`** (RNF-3): el export de dependencias es
  `uv export --locked --no-dev --no-emit-project --format requirements-txt` a un archivo
  temporal del job; no se versiona ningún `requirements.txt`. La auditoría corre con
  `uvx --from pip-audit==2.10.1`, nunca con `pip install`.
- **Sin secretos del repositorio** (RNF-1): los jobs solo leen el código; el único valor
  efímero (`M2_DOWNLOAD_SECRET`) lo genera el job de pruebas, no el de seguridad.
- **El escaneo no entra en `make check`**: igual que `make corpus-dorado`, necesita red
  (consulta de advisories y descarga de gitleaks). `make security` es el objetivo propio y
  es el que ejecutan los dos pipelines. `make check` sigue siendo offline.
- **Severidad alta (RF-3/AC2)** no viene en el reporte de `pip-audit`, así que la regla se
  hace explícita en la política: bloquea un advisory **con corrección publicada**, **de
  severidad alta o crítica** (base CVSS v3 ≥ 7,0, o `database_specific.severity` de OSV), o
  **no clasificable** — en ese último caso se falla cerrado. Un advisory sin corrección y
  sin severidad alta se informa y no bloquea.
- **Excepciones (RF-4, AC3)**: se declaran en `security/excepciones-*.toml` con
  `justificacion`, `aprobado_por` y `revision` (fecha ISO); el validador falla si falta
  cualquiera de los tres o si la fecha ya pasó. Un hallazgo exceptuado y vigente no bloquea,
  pero **sigue apareciendo en la salida** del job: la excepción es visible en el repositorio
  y en el log.
- **Fixtures de AC1**: `tests/fixtures/seguridad/secreto-falso.env` contiene una clave falsa
  de alta entropía con forma de API key genérica, sin prefijo de ningún proveedor: la
  protección de push de GitHub bloquea valores con forma de clave real (p. ej. `sk-…`). `tests/fixtures/seguridad/` está excluido de forma explícita en
  `.gitleaks.toml` (allowlist con descripción) para que el repositorio quede limpio, y una
  prueba corre gitleaks sobre el fixture sin la exclusión para demostrar que la regla sí lo
  detecta. Ninguna credencial real entra al repositorio.
- **Fuera de alcance**: SAST, imágenes Docker, escaneo npm y un hook de pre-commit (la
  especificación pide jobs de CI; el hook queda como seguimiento).

## Estado de `main` frente al escaneo (hallazgo real, pendiente de decisión)

Con las herramientas fijadas, el 27/11 sobre `4f689ed`:

- **Secretos**: `gitleaks 8.30.1` sobre 189 commits → **0 hallazgos**. `main` pasa AC1.
- **Dependencias**: `pip-audit 2.10.1` sobre el export de `uv.lock` (148 paquetes) →
  **46 advisories en 3 paquetes**:

  | Paquete | Versión | Advisories | Corrección | Severidad OSV |
  |---|---:|---:|---|---|
  | `pillow` | 12.3.0 | 42 | **13.0.0** | una HIGH explícita, el resto con vector CVSS v3 (varias ≥ 7,0) |
  | `vtk` | 9.3.1 | 3 | **9.5.1** | sin severidad publicada; sin vector en OSV |
  | `diskcache` | 5.6.3 | 2 (mismo advisory) | **ninguna** | `CVE-2025-69872`, solo vector CVSS v4 |

  Con la regla de arriba, `main` **no pasa**: los advisories de `pillow` y `vtk` tienen
  corrección publicada y `diskcache` no es clasificable. No se silencia nada: el archivo de
  excepciones se entrega vacío y la decisión (subir `pillow`/`vtk` o aprobar excepciones con
  fecha) queda para el responsable, que es quien aprueba excepciones según la política.

`uv lock --upgrade-package pillow --dry-run` resuelve `12.3.0 → 13.0.0` sin conflicto, así
que la corrección de `pillow` es viable en una sola línea de lock; `vtk` está atado al
kernel CAD vendoreado y `diskcache` entra por `mlflow`.

## Pruebas

`tests/test_seguridad_ci.py` (AAA, sin red ni herramientas externas):

- AC1: un reporte de gitleaks con un hallazgo produce archivo, línea, regla y los tres pasos
  (rotar, retirar del historial, declarar excepción); un reporte vacío produce el mensaje de
  paso.
- AC2: una auditoría con `jinja2 2.11.2` (CVE-2024-34064, corrección 3.1.5) y severidad alta
  produce paquete, CVE, versión corregida y el comando de `uv` para actualizar.
- AC3: una excepción vigente y justificada desbloquea el hallazgo pero sigue informándose;
  sin justificación, sin aprobador o con fecha vencida el validador falla.
- Clasificación de severidad: vectores CVSS v3 conocidos → base score y etiqueta.

`tests/test_ci_parity.py` crece con las invariantes nuevas: los dos pipelines corren los
mismos comandos de seguridad, con las mismas versiones fijadas, y ninguno usa `pip install`.
