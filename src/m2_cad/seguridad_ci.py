"""Escaneo de seguridad en CI: secretos y dependencias (SPEC-029, HU-28).

Lógica pura del escaneo: clasifica la auditoría de `pip-audit`, arma los reportes
en español con el paso exacto a seguir y valida la política de excepciones. No
importa herramientas externas, no descarga nada y no usa red: es importable con
la biblioteca estándar y se prueba desde `tests/test_seguridad_ci.py`.

Regla de bloqueo (RF-1, RF-3, AC2): un hallazgo de dependencia **bloquea** salvo
que exista una excepción para su advisory/CVE, declarada en
`security/excepciones-dependencias.toml`, con `revision` vigente (hoy o después).
Se considera bloqueante todo advisory **con corrección publicada** (`fix_versions`)
o de severidad `alta`, `crítica` o `desconocida` — esta última falla cerrado
porque una severidad no clasificable no puede declararse segura. Un advisory sin
corrección y de severidad `media` o `baja` se informa sin bloquear. Una excepción
vencida **no** desbloquea: el hallazgo vuelve a bloquear y el reporte la nombra.

Las excepciones válidas se declaran en `security/excepciones-*.toml` (RF-4): cada
entrada exige `justificacion` (obligatoria, ≥ 20 caracteres), `aprobado_por`,
`revision` (fecha ISO, hoy o después y como máximo 180 días vista) y los campos
propios de la herramienta (`advisory` y `paquete`, o `archivo`, `linea` y `regla`).

Versiones fijadas (RNF-2): gitleaks 8.30.1 y pip-audit==2.10.1, este último siempre
lanzado como `uvx --from pip-audit==2.10.1`; nunca se instala con pip.
"""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Sequence

# Versiones exactas fijadas (RNF-2). El asset y su sha256 también se fijan aquí
# para que la descarga del binario sea verificable sin confiar en la red.
VERSION_GITLEAKS = "8.30.1"
VERSION_PIP_AUDIT = "2.10.1"
ESPECIFICACION_PIP_AUDIT = f"pip-audit=={VERSION_PIP_AUDIT}"
URL_GITLEAKS_LINUX_X64 = (
    "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/"
    "gitleaks_8.30.1_linux_x64.tar.gz"
)
SHA256_GITLEAKS_LINUX_X64 = "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"

RUTA_EXCEPCIONES_SECRETOS = Path("security/excepciones-secretos.toml")
RUTA_EXCEPCIONES_DEPENDENCIAS = Path("security/excepciones-dependencias.toml")

SEVERIDADES_QUE_BLOQUEAN = ("alta", "crítica", "desconocida")
SEVERIDADES = ("crítica", "alta", "media", "baja", "desconocida")
MINIMO_JUSTIFICACION = 20
MAXIMO_DIAS_REVISION = 180

_CAMPOS_POR_HERRAMIENTA = {
    "secretos": ("archivo", "linea", "regla"),
    "dependencias": ("advisory", "paquete"),
}

_CLAVES_DE_EXCEPCIONES = ("excepciones",)


# ---------------------------------------------------------------------------
# Severidad
# ---------------------------------------------------------------------------

# Pesos de CVSS v3.0/3.1 (especificación CVSS v3.1, sección 7.4).
_PESOS = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20},
    "AC": {"L": 0.77, "H": 0.44},
    "UI": {"N": 0.85, "R": 0.62},
    "PR": {
        "U": {"N": 0.85, "L": 0.62, "H": 0.27},
        "C": {"N": 0.85, "L": 0.68, "H": 0.50},
    },
    "CIA": {"H": 0.56, "L": 0.22, "N": 0.0},
}

_NOMBRE_SEVERIDAD = {
    "CRITICAL": "crítica",
    "HIGH": "alta",
    "MODERATE": "media",
    "LOW": "baja",
}

_ORDEN_SEVERIDAD = {"crítica": 0, "alta": 1, "desconocida": 2, "media": 3, "baja": 4}


def _metricas_cvss_v3(vector: str) -> dict[str, str]:
    """Descompone un vector CVSS v3.0/3.1 y valida las ocho métricas base."""
    partes = vector.strip().split("/")
    if not partes or not partes[0].upper().startswith("CVSS:3."):
        raise ValueError(f"vector CVSS v3 esperado, recibido: {vector!r}")
    metricas: dict[str, str] = {}
    for parte in partes[1:]:
        clave, _, valor = parte.partition(":")
        metricas[clave.upper()] = valor.upper()
    for clave in ("AV", "AC", "PR", "UI", "S", "C", "I", "A"):
        if clave not in metricas:
            raise ValueError(f"al vector CVSS v3 le falta la métrica {clave}: {vector!r}")
    return metricas


def _redondear_al_alza(puntuacion: float) -> float:
    """Redondeo hacia arriba de CVSS v3.1 (apéndice A), sin errores binarios."""
    entero = int(round(puntuacion * 100000))
    if entero % 10000 == 0:
        return entero / 100000.0
    return (math.floor(entero / 10000) + 1) / 10.0


def severidad_cvss_v3(vector: str) -> float:
    """Puntuación base de un vector CVSS v3.0/3.1; `ValueError` si es inválido."""
    metricas = _metricas_cvss_v3(vector)
    for clave in ("AV", "AC", "UI", "C", "I", "A"):
        tabla = _PESOS["CIA"] if clave in ("C", "I", "A") else _PESOS[clave]
        if metricas[clave] not in tabla:
            raise ValueError(f"métrica {clave}={metricas[clave]} desconocida en {vector!r}")
    if metricas["S"] not in ("U", "C"):
        raise ValueError(f"métrica S={metricas['S']} desconocida en {vector!r}")
    alcance = metricas["S"]
    if metricas["PR"] not in _PESOS["PR"][alcance]:
        raise ValueError(f"métrica PR={metricas['PR']} desconocida en {vector!r}")

    confidencialidad = _PESOS["CIA"][metricas["C"]]
    integridad = _PESOS["CIA"][metricas["I"]]
    disponibilidad = _PESOS["CIA"][metricas["A"]]
    iss = 1 - (1 - confidencialidad) * (1 - integridad) * (1 - disponibilidad)
    if alcance == "U":
        impacto = 6.42 * iss
    else:
        impacto = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
    explotabilidad = (
        8.22
        * _PESOS["AV"][metricas["AV"]]
        * _PESOS["AC"][metricas["AC"]]
        * _PESOS["PR"][alcance][metricas["PR"]]
        * _PESOS["UI"][metricas["UI"]]
    )
    if impacto <= 0:
        return 0.0
    if alcance == "U":
        base = min(impacto + explotabilidad, 10.0)
    else:
        base = min(1.08 * (impacto + explotabilidad), 10.0)
    return _redondear_al_alza(base)


def severidad_de_osv(osv: dict) -> str:
    """Severidad de un advisory de OSV en español (RF-3, AC2).

    Se usa `database_specific.severity` cuando publica HIGH/CRITICAL/MODERATE/LOW;
    si no, la mayor puntuación base de los vectores CVSS v3 de `severity[].score`.
    Un advisory solo con CVSS v4, sin severidad publicada, queda `"desconocida"`
    y por tanto bloquea (se falla cerrado).
    """
    datos = osv.get("database_specific") or {}
    if isinstance(datos, dict):
        publicada = str(datos.get("severity") or "").strip().upper()
        if publicada in _NOMBRE_SEVERIDAD:
            return _NOMBRE_SEVERIDAD[publicada]
    puntuaciones: list[float] = []
    for entrada in osv.get("severity") or []:
        if not isinstance(entrada, dict):
            continue
        if str(entrada.get("type") or "").strip().upper() != "CVSS_V3":
            continue
        vector = entrada.get("score")
        if not isinstance(vector, str) or not vector.upper().startswith("CVSS:3"):
            continue
        try:
            puntuaciones.append(severidad_cvss_v3(vector))
        except ValueError:
            continue
    if not puntuaciones:
        return "desconocida"
    mayor = max(puntuaciones)
    if mayor >= 9.0:
        return "crítica"
    if mayor >= 7.0:
        return "alta"
    if mayor >= 4.0:
        return "media"
    return "baja"


def _normalizar_severidad(severidad: str | None) -> str:
    """Cualquier etiqueta fuera de la escala se trata como `desconocida` (RF-3)."""
    valor = str(severidad or "").strip().lower()
    return valor if valor in SEVERIDADES else "desconocida"


# ---------------------------------------------------------------------------
# Dependencias
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HallazgoDependencia:
    """Un advisory de `pip-audit` para un paquete instalado (una fila del reporte)."""

    paquete: str
    version: str
    advisory: str
    cve: str
    severidad: str
    correccion: str | None
    bloqueante: bool
    excepcion: dict | None = None
    excepcion_vencida: bool = False


def _cve(vuln: dict, advisory: str) -> str:
    """Primer alias con forma de CVE; si no hay, el id del advisory."""
    for alias in vuln.get("aliases") or []:
        texto = str(alias).strip().upper()
        if texto.startswith("CVE-"):
            return texto
    return advisory


def _fecha(valor: object) -> date | None:
    """Fecha ISO (`AAAA-MM-DD`) o `None` si el valor no es válido."""
    if isinstance(valor, date):
        return valor
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        return date.fromisoformat(valor.strip())
    except ValueError:
        return None


def _referencias(entrada: dict) -> set[str]:
    """Identificadores con los que una excepción puede casar (advisory o CVE)."""
    referencias = set()
    for clave in ("advisory", "cve"):
        valor = str(entrada.get(clave) or "").strip().upper()
        if valor:
            referencias.add(valor)
    return referencias


def _buscar_excepcion(
    excepciones: Iterable[dict], paquete: str, advisory: str, cve: str, hoy: date
) -> tuple[dict | None, bool]:
    """Excepción aplicable al hallazgo y si está vencida (RF-4, AC3).

    Devuelve `(None, False)` si no hay excepción, `(entrada, False)` si está
    vigente y `(entrada, True)` si su fecha de revisión ya pasó — en ese caso no
    desbloquea y el reporte lo dice.
    """
    buscados = {advisory.upper(), cve.upper()}
    encontrada: dict | None = None
    vencida = False
    for entrada in excepciones:
        if not isinstance(entrada, dict):
            continue
        if str(entrada.get("paquete") or "").strip().lower() != paquete.strip().lower():
            continue
        if not (_referencias(entrada) & buscados):
            continue
        fecha = _fecha(entrada.get("revision"))
        vencida_entrada = fecha is None or fecha < hoy
        if not vencida_entrada:
            return entrada, False
        encontrada, vencida = entrada, True
    return encontrada, vencida


def clasificar_dependencias(
    auditoria: dict,
    severidades: dict[str, str],
    excepciones: list[dict],
    hoy: date,
) -> list[HallazgoDependencia]:
    """Clasifica el JSON de `pip-audit` en un hallazgo por (paquete, advisory).

    Regla de bloqueo (RF-1, RF-3, AC2): un hallazgo bloquea si tiene corrección
    publicada o si su severidad es `alta`, `crítica` o `desconocida`; una
    excepción vigente (revisión hoy o después) lo desbloquea y una vencida no.
    """
    hallazgos: list[HallazgoDependencia] = []
    vistos: set[tuple[str, str]] = set()
    for dependencia in auditoria.get("dependencies") or []:
        if not isinstance(dependencia, dict):
            continue
        paquete = str(dependencia.get("name") or "").strip()
        version = str(dependencia.get("version") or "").strip()
        for vuln in dependencia.get("vulns") or []:
            if not isinstance(vuln, dict):
                continue
            advisory = str(vuln.get("id") or "").strip()
            if not advisory or (paquete, advisory) in vistos:
                continue
            vistos.add((paquete, advisory))
            correcciones = [str(fix) for fix in vuln.get("fix_versions") or [] if fix]
            correccion = correcciones[0] if correcciones else None
            severidad = _normalizar_severidad(severidades.get(advisory))
            cve = _cve(vuln, advisory)
            excepcion, vencida = _buscar_excepcion(excepciones, paquete, advisory, cve, hoy)
            vigente = excepcion is not None and not vencida
            bloqueo_base = correccion is not None or severidad in SEVERIDADES_QUE_BLOQUEAN
            hallazgos.append(
                HallazgoDependencia(
                    paquete=paquete,
                    version=version,
                    advisory=advisory,
                    cve=cve,
                    severidad=severidad,
                    correccion=correccion,
                    bloqueante=bloqueo_base and not vigente,
                    excepcion=excepcion,
                    excepcion_vencida=vencida,
                )
            )
    return hallazgos


def _plural(cantidad: int, singular: str, plural: str) -> str:
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _lineas_hallazgo_dependencia(hallazgo: HallazgoDependencia) -> list[str]:
    correccion = hallazgo.correccion or "sin versión corregida"
    lineas = [
        f"- {hallazgo.paquete} {hallazgo.version} · {hallazgo.cve} ({hallazgo.advisory}) · "
        f"severidad {hallazgo.severidad} · corrección: {correccion}"
    ]
    if hallazgo.excepcion is not None:
        estado = "excepción vencida" if hallazgo.excepcion_vencida else "excepción vigente"
        lineas.append(
            f"  {estado}: revisión {hallazgo.excepcion.get('revision')} · "
            f"aprobada por {hallazgo.excepcion.get('aprobado_por')} · "
            f"justificación: {hallazgo.excepcion.get('justificacion')}"
        )
    if hallazgo.bloqueante:
        accion = f"  Acción: uv lock --upgrade-package {hallazgo.paquete}"
        if hallazgo.correccion:
            accion += f' && uv add "{hallazgo.paquete}>={hallazgo.correccion}"'
        lineas.append(accion)
        if hallazgo.excepcion_vencida:
            lineas.append(
                "  La excepción venció: vuelve a bloquear hasta que se revise o se corrija."
            )
        lineas.append(
            "  Alternativa: declarar una excepción justificada en "
            "security/excepciones-dependencias.toml (justificacion, aprobado_por, revision)."
        )
    return lineas


def mensaje_dependencias(
    hallazgos: Sequence[HallazgoDependencia],
    paquetes_auditados: int | None = None,
    no_auditables: Iterable[str] = (),
) -> str:
    """Reporte en español del escaneo de dependencias (RF-1, RF-3, AC2, AC3).

    Cada hallazgo bloqueante nombra el paquete, la versión instalada, el CVE, la
    versión corregida (o `sin versión corregida`) y el comando exacto para
    actualizar. La última línea es siempre `RESULTADO: ...` (RF-3).
    """
    hallazgos = list(hallazgos)
    no_auditables = list(no_auditables)
    if paquetes_auditados is None:
        paquetes_auditados = len({hallazgo.paquete for hallazgo in hallazgos})
    lineas = [
        "Auditoría de dependencias: pip-audit sobre el export de uv.lock.",
        "Política de excepciones: security/excepciones-dependencias.toml.",
        "",
    ]
    if no_auditables:
        lineas.append("Requisitos no auditables desde un índice (no bloquean):")
        lineas.extend(f"- {nombre}" for nombre in no_auditables)
        lineas.append("")
    bloqueantes = [hallazgo for hallazgo in hallazgos if hallazgo.bloqueante]
    informativos = [hallazgo for hallazgo in hallazgos if not hallazgo.bloqueante]
    if bloqueantes:
        total = _plural(len(bloqueantes), "hallazgo", "hallazgos")
        lineas.append(f"Hallazgos bloqueantes ({total}):")
        for hallazgo in sorted(bloqueantes, key=lambda item: _ORDEN_SEVERIDAD[item.severidad]):
            lineas.extend(_lineas_hallazgo_dependencia(hallazgo))
            lineas.append("")
    if informativos:
        lineas.append("Hallazgos informacionales (no bloquean):")
        for hallazgo in informativos:
            lineas.extend(_lineas_hallazgo_dependencia(hallazgo))
        lineas.append("")
    if bloqueantes:
        total = _plural(len(bloqueantes), "hallazgo bloqueante", "hallazgos bloqueantes")
        lineas.append(f"RESULTADO: {total} — el job falla (RF-3).")
    else:
        lineas.append(
            "RESULTADO: auditoría de dependencias superada: "
            f"{_plural(paquetes_auditados, 'paquete auditado', 'paquetes auditados')} "
            "sin hallazgos bloqueantes."
        )
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Secretos
# ---------------------------------------------------------------------------


def _excepcion_de_secreto(
    excepciones: Iterable[dict], hallazgo: dict, hoy: date
) -> tuple[dict | None, bool]:
    """Excepción aplicable a un hallazgo de gitleaks y si está vencida (AC1, AC3)."""
    archivo = str(hallazgo.get("File") or "").strip().lstrip("./")
    regla = str(hallazgo.get("RuleID") or "").strip()
    try:
        linea = int(hallazgo.get("StartLine"))
    except (TypeError, ValueError):
        return None, False
    encontrada: dict | None = None
    vencida = False
    for entrada in excepciones:
        if not isinstance(entrada, dict):
            continue
        if str(entrada.get("archivo") or "").strip().lstrip("./") != archivo:
            continue
        if str(entrada.get("regla") or "").strip() != regla:
            continue
        try:
            if int(entrada.get("linea")) != linea:
                continue
        except (TypeError, ValueError):
            continue
        fecha = _fecha(entrada.get("revision"))
        if fecha is not None and fecha >= hoy:
            return entrada, False
        encontrada, vencida = entrada, True
    return encontrada, vencida


def secretos_bloqueantes(
    hallazgos: Sequence[dict],
    excepciones: Iterable[dict] = (),
    hoy: date | None = None,
) -> list[dict]:
    """Hallazgos de gitleaks que bloquean (RF-3, AC1, AC3).

    Un hallazgo bloquea salvo que una excepción vigente lo cubra: es la misma
    regla que aplica `mensaje_secretos`, expuesta para los scripts.
    """
    hoy = hoy or date.today()
    excepciones = list(excepciones)
    bloqueantes = []
    for hallazgo in hallazgos:
        if not isinstance(hallazgo, dict):
            continue
        excepcion, vencida = _excepcion_de_secreto(excepciones, hallazgo, hoy)
        if excepcion is None or vencida:
            bloqueantes.append(hallazgo)
    return bloqueantes


def mensaje_secretos(
    hallazgos: Sequence[dict],
    excepciones: Iterable[dict] = (),
    hoy: date | None = None,
) -> str:
    """Reporte en español del escaneo de secretos (RF-2, RF-3, AC1, AC3).

    Cada hallazgo no exceptuado nombra `archivo:línea`, la regla y los tres pasos
    permitidos: rotar la clave, retirarla del historial o declarar una excepción
    justificada. Las excepciones vigentes quedan visibles con su justificación y
    su fecha de revisión; una excepción vencida no desbloquea.
    """
    hoy = hoy or date.today()
    hallazgos = list(hallazgos)
    excepciones = list(excepciones)
    lineas = [
        "Escaneo de secretos: gitleaks sobre el historial del repositorio.",
        "Política de excepciones: security/excepciones-secretos.toml.",
        "",
    ]
    bloqueantes = 0
    for hallazgo in hallazgos:
        if not isinstance(hallazgo, dict):
            continue
        archivo = str(hallazgo.get("File") or "(archivo desconocido)").strip()
        linea = hallazgo.get("StartLine")
        regla = str(hallazgo.get("RuleID") or "(regla desconocida)").strip()
        excepcion, vencida = _excepcion_de_secreto(excepciones, hallazgo, hoy)
        bloqueante = excepcion is None or vencida
        encabezado = f"- {archivo}:{linea} · regla {regla}"
        if bloqueante:
            bloqueantes += 1
            encabezado += " · BLOQUEANTE"
        lineas.append(encabezado)
        descripcion = str(hallazgo.get("Description") or "").strip()
        if descripcion:
            lineas.append(f"  Detalle: {descripcion}")
        if hallazgo.get("Commit"):
            lineas.append(f"  Commit: {hallazgo['Commit']}")
        if excepcion is not None:
            estado = "excepción vencida" if vencida else "excepción vigente"
            lineas.append(
                f"  {estado}: revisión {excepcion.get('revision')} · "
                f"aprobada por {excepcion.get('aprobado_por')} · "
                f"justificación: {excepcion.get('justificacion')}"
            )
        if bloqueante:
            lineas.extend(
                [
                    "  Pasos permitidos:",
                    "    1) rotar la clave en el proveedor",
                    "    2) retirarla del historial (por ejemplo con git filter-repo)",
                    "    3) declarar una excepción justificada en "
                    "security/excepciones-secretos.toml",
                ]
            )
        lineas.append("")
    if bloqueantes:
        lineas.append(
            f"RESULTADO: {_plural(bloqueantes, 'hallazgo bloqueante', 'hallazgos bloqueantes')}"
            " — ningún secreto puede fusionarse (AC1)."
        )
    else:
        lineas.append(
            "RESULTADO: escaneo de secretos superado: no hay secretos bloqueantes en el historial."
        )
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Política de excepciones (RF-4)
# ---------------------------------------------------------------------------


def leer_toml(ruta: Path) -> dict:
    """Lee un archivo TOML de excepciones desde disco (UTF-8, sin red)."""
    return tomllib.loads(Path(ruta).read_text(encoding="utf-8"))


def cargar_excepciones(ruta: Path) -> list[dict]:
    """Entradas `[[excepciones]]` del archivo; `[]` si no hay ninguna declarada."""
    datos = leer_toml(ruta)
    entradas = datos.get("excepciones", [])
    if not isinstance(entradas, list):
        raise ValueError(f"{ruta}: `excepciones` debe ser una lista de tablas ([[excepciones]])")
    return [entrada for entrada in entradas if isinstance(entrada, dict)]


def _validar_entrada(entrada: dict, herramienta: str, hoy: date, etiqueta: str) -> list[str]:
    errores: list[str] = []
    justificacion = entrada.get("justificacion")
    if not isinstance(justificacion, str) or not justificacion.strip():
        errores.append(f"{etiqueta}: falta `justificacion` (obligatoria)")
    elif len(justificacion.strip()) < MINIMO_JUSTIFICACION:
        errores.append(
            f"{etiqueta}: `justificacion` debe explicar por qué el hallazgo no se puede "
            f"corregir (mínimo {MINIMO_JUSTIFICACION} caracteres)"
        )
    aprobado_por = entrada.get("aprobado_por")
    if not isinstance(aprobado_por, str) or not aprobado_por.strip():
        errores.append(f"{etiqueta}: falta `aprobado_por` (quién aprueba la excepción)")
    for campo in _CAMPOS_POR_HERRAMIENTA[herramienta]:
        valor = entrada.get(campo)
        if campo == "linea":
            try:
                numero = int(valor)
            except (TypeError, ValueError):
                errores.append(f"{etiqueta}: falta `linea` (número de línea del hallazgo)")
                continue
            if numero < 1:
                errores.append(f"{etiqueta}: `linea` debe ser un número de línea positivo")
            continue
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            errores.append(f"{etiqueta}: falta `{campo}`")
    revision = entrada.get("revision")
    fecha = _fecha(revision)
    if revision is None or (isinstance(revision, str) and not revision.strip()):
        errores.append(f"{etiqueta}: falta `revision` (fecha ISO AAAA-MM-DD)")
    elif fecha is None:
        errores.append(f"{etiqueta}: `revision` no es una fecha ISO válida: {revision!r}")
    elif fecha < hoy:
        errores.append(
            f"{etiqueta}: `revision` vencida ({revision}); la fecha debe ser hoy o posterior"
        )
    elif fecha > hoy + timedelta(days=MAXIMO_DIAS_REVISION):
        errores.append(
            f"{etiqueta}: `revision` ({revision}) supera los {MAXIMO_DIAS_REVISION} días "
            "que admite la política"
        )
    return errores


def validar_excepciones(datos: dict, herramienta: str, hoy: date) -> list[str]:
    """Valida la política de excepciones y devuelve los errores en español (RF-4).

    Exige `justificacion` (obligatoria, ≥ 20 caracteres), `aprobado_por` y
    `revision` (fecha ISO vigente y como máximo 180 días vista), más los campos
    propios de la herramienta. Rechaza claves desconocidas en el nivel superior y
    entradas que no sean tablas. Lista vacía significa archivo válido.
    """
    if herramienta not in _CAMPOS_POR_HERRAMIENTA:
        raise ValueError(f"herramienta desconocida: {herramienta!r}")
    errores: list[str] = []
    for clave in datos:
        if clave not in _CLAVES_DE_EXCEPCIONES:
            errores.append(f"clave desconocida en las excepciones de {herramienta}: `{clave}`")
    entradas = datos.get("excepciones", [])
    if not isinstance(entradas, list):
        errores.append(
            f"excepciones de {herramienta}: `excepciones` debe ser una lista de tablas "
            "([[excepciones]])"
        )
        return errores
    for posicion, entrada in enumerate(entradas, start=1):
        etiqueta = f"excepción #{posicion} de {herramienta}"
        if not isinstance(entrada, dict):
            errores.append(f"{etiqueta}: cada entrada de [[excepciones]] debe ser una tabla")
            continue
        errores.extend(_validar_entrada(entrada, herramienta, hoy, etiqueta))
    return errores
