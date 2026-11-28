"""Pipeline de generación y verificación geométrica (HU-04).

Convierte la solicitud en español en un programa constraint-kit, lo valida
contra el verificador de constraint-kit, construye la pieza B-rep y entrega
STEP, GLB y lista de materiales en CSV, con el tiempo de generación y de
construcción de cada solicitud.

Especificación: specs/002-step-verificado/spec.md
- AC1: el programa pasa el verificador de constraint-kit sin errores.
- AC2: el STEP es un B-rep de OpenCascade.
- AC3: volumen y caja envolvente dentro de ±2 % del valor esperado.
- AC4: cada respuesta entrega STEP, GLB y CSV.
- AC5: se registra el tiempo de generación y de construcción.

HU-05 (specs/003-declinacion-preliminar/spec.md): declina con motivo en
español y sin STEP lo que está fuera del catálogo, y marca todo STEP como
diseño preliminar.

HU-14: la solicitud en español llega directa al modelo, sin traducción ES→EN.
"""

import csv
import io
import json
import logging
import os
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx
from constraint_kit import builder, dsl, llm

from m2_cad import (
    MARCA_PRELIMINAR,
    declinacion,
    llm_resiliente,
    materiales,
    plano_dxf,
    plano_pdf,
    prompts,
)
from m2_cad.control import ControlGeneracion
from m2_cad.observabilidad import job_id_actual, redactar
from m2_cad.registro import _sanitizar

logger = logging.getLogger(__name__)

RUTA_SALIDA = Path("outputs")
NOMBRE_PIEZA = "pieza"
# Columnas del BOM (HU-48, SPEC-049): las cuatro primeras son las históricas y
# conservan su nombre y su orden para no romper a sus consumidores (RNF-3).
COLUMNAS_BOM = (
    "part_type",
    "qty",
    "total_mass_g",
    "unit_mass_g",
    "material",
    "unit_cost_usd",
    "total_cost_usd",
)
# Plazo total de la llamada al LLM, repartido entre todos los reintentos (HU-25).
TIEMPO_ESPERA_LLM = 120.0
TEMPERATURA_LLM = 0.1

# Frontera de validez del producto (HU-02/HU-05): tipo del motor -> nombre en español.
CATALOGO = {
    "plate": "placa",
    "sheet_bracket": "escuadra de chapa",
    "adapter": "adaptador",
    "flange": "brida",
    "spacer": "espaciador",
    "screw": "tornillo",
    "extrusion": "perfil extruido",
    "pipe": "tubo",
}
# HU-26: el prefijo y el catálogo de causas viven en `declinacion` (una sola fuente).

# Prompt de sistema para DeepSeek (HU-14): el texto vive como artefacto versionado
# en `prompts/planner-v1.txt` (id, versión y sha256 en `prompts/manifest.toml`) y
# se carga por id con `prompts.cargar()` (HU-33, SPEC-034). El prompt describe los
# parámetros de cada tipo del catálogo (firmas de constraint_kit/parts.py y
# parts_bd.py, ejemplos del banco HU-02) y recibe la solicitud en español, sin
# traducción previa. `PROMPT_SISTEMA` se conserva para `_respuesta_modelo` y las
# pruebas de no regresión de HU-14.
PROMPT_VIGENTE = prompts.cargar()
PROMPT_SISTEMA = PROMPT_VIGENTE.texto

# Prompt de edición (HU-35, SPEC-036): artefacto versionado propio
# (`prompts/editor-v1.txt`, id `editor` en el manifiesto). Recibe el programa DSL
# vigente y una instrucción de cambio en español, aplica solo ese cambio y repite
# la regla de honestidad del planificador. `planner-v1` no se toca.
PROMPT_EDICION = prompts.cargar("editor")

# Mensajes en español para los estados HTTP más comunes de DeepSeek (HU-14, AC3).
MENSAJES_HTTP = {
    401: "DeepSeek rechazó la API key (HTTP 401). Revisa DEEPSEEK_API_KEY.",
    402: "La cuenta de DeepSeek no tiene saldo suficiente (HTTP 402).",
    429: "Se alcanzó el límite de solicitudes de DeepSeek (HTTP 429). Intenta más tarde.",
}


class ErrorPipeline(RuntimeError):
    """Error base del pipeline de generación."""


class ModeloNoDisponible(ErrorPipeline):
    """El modelo servido (HU-01) no está configurado o no responde."""


class ErrorGeneracion(ErrorPipeline):
    """La salida del modelo no contiene un programa interpretable (HU-26, RF-2)."""

    def __init__(
        self, detalle: str, *, causa: declinacion.Causa = declinacion.Causa.TEXTO_AMBIGUO
    ) -> None:
        super().__init__(detalle)
        # RF-5: el detalle técnico se conserva para diagnóstico.
        self.detalle = detalle
        self.causa = causa
        self.mensaje = declinacion.mensaje(causa)


class ErrorVerificacion(ErrorPipeline):
    """El programa no pasa el verificador de constraint-kit (AC1).

    `str(exc)` sigue siendo el diagnóstico técnico; `mensaje` es lo que lee el
    usuario y `causa` la etiqueta estructurada (HU-26, RF-3 a RF-5).
    """

    def __init__(
        self, detalle: str, *, causa: declinacion.Causa = declinacion.Causa.VERIFICACION_FALLIDA
    ) -> None:
        super().__init__(detalle)
        self.detalle = detalle
        self.causa = causa
        self.mensaje = declinacion.mensaje(causa)


class PiezaDeclinada(ErrorPipeline):
    """La pieza no se construye; `motivo` es legible en español (HU-05, AC1).

    HU-26: `causa` es la etiqueta del catálogo que usan el registro y el seguimiento;
    `detalle` conserva la razón técnica, que nunca se muestra como mensaje.
    """

    def __init__(
        self,
        motivo: str,
        detalle: str | None = None,
        *,
        causa: declinacion.Causa = declinacion.Causa.FAMILIA_NO_SOPORTADA,
    ) -> None:
        super().__init__(f"Pieza declinada: {motivo}")
        self.motivo = motivo
        self.detalle = detalle
        self.causa = causa
        # Programa que originó la declinación, para el seguimiento (HU-16, AC2).
        self.programa_json: Path | None = None

    @property
    def mensaje(self) -> str:
        """Mensaje que lee el usuario: el motivo ya legible (AC2)."""
        return self.motivo


def _declinar(
    causa: declinacion.Causa,
    contexto: str | None = None,
    detalle: str | None = None,
) -> PiezaDeclinada:
    catalogo = ", ".join(CATALOGO.values())
    return PiezaDeclinada(
        declinacion.mensaje(causa, contexto, catalogo=catalogo), detalle, causa=causa
    )


class ProgramaLLM(dict):
    """Programa compatible con dict que conserva la identidad reportada por el servidor."""

    version_modelo: str = "desconocida"


@dataclass(frozen=True)
class ResultadoPieza:
    """Entregables y métricas de una pieza construida (AC4 y AC5)."""

    programa: dict
    step: Path
    glb: Path
    bom_csv: Path
    volumen_mm3: float
    caja_mm: tuple[float, float, float]
    tiempo_construccion_s: float
    tiempo_generacion_s: float = 0.0
    familia: str = ""
    programa_json: Path | None = None
    version_modelo: str = "desconocida"
    #: Firma geométrica del núcleo (`dsl.signature`), para HU-49 (AC3).
    firma: dict | None = None
    #: Plano DXF de vistas ortogonales (SPEC-043); None en dobles de prueba.
    dxf: Path | None = None
    #: Plano PDF con cajetín (SPEC-044); None en dobles de prueba.
    pdf: Path | None = None
    #: Partes del ensamble con material y masa, para el cajetín del plano (SPEC-044 RF-2).
    partes: list[dict] | None = None

    def a_respuesta(self) -> dict[str, str]:
        """Serializa el resultado para la API (todos los valores como texto)."""
        respuesta = {
            "step": str(self.step),
            "glb": str(self.glb),
            "bom_csv": str(self.bom_csv),
            "aviso": MARCA_PRELIMINAR,
            "volumen_mm3": f"{self.volumen_mm3:.2f}",
            "caja_mm": "x".join(f"{lado:.2f}" for lado in self.caja_mm),
            "tiempo_generacion_s": f"{self.tiempo_generacion_s:.3f}",
            "tiempo_construccion_s": f"{self.tiempo_construccion_s:.3f}",
        }
        if self.dxf is not None:  # SPEC-043: el plano DXF es aditivo
            respuesta["dxf"] = str(self.dxf)
        if self.pdf is not None:  # SPEC-044: el plano PDF es aditivo
            respuesta["pdf"] = str(self.pdf)
        return respuesta


def extraer_programa(salida: str) -> dict:
    """Extrae el último objeto JSON de nivel superior de la salida del modelo.

    El modelo afinado puede anteponer razonamiento y delimitadores de canal
    (mismo criterio que vendor/constraint-kit/training/grpo_reward.py). El
    decodificador JSON respeta las llaves que aparecen dentro de cadenas.
    """
    texto = salida.split("<channel|>")[-1].split("<turn|>")[0]
    decodificador = json.JSONDecoder()
    programa = None
    indice = texto.find("{")
    while indice != -1:
        try:
            objeto, fin = decodificador.raw_decode(texto, indice)
        except json.JSONDecodeError:
            indice = texto.find("{", indice + 1)
            continue
        if isinstance(objeto, dict):
            programa = objeto
        indice = texto.find("{", fin)
    if programa is None:
        raise ErrorGeneracion("La salida del modelo no contiene un programa JSON.")
    return programa


def _material_pedido(pedido: object) -> str | None:
    """Texto del material pedido, o `None` si no lo hay (vacío o no es texto)."""
    if isinstance(pedido, str) and pedido.strip():
        return pedido.strip()
    return None


def validar_materiales(programa: dict) -> None:
    """Normaliza el alias del material y declina lo que no está soportado (RF-2, RF-5).

    El verificador del kit acepta cualquier texto y construye con la densidad del acero en
    silencio; este guard es el único punto que conoce el catálogo real
    (`materiales.SOPORTADOS`). Corre antes del verificador, así que también cubre a quien
    llama `construir_pieza` sin pasar por el catálogo de familias (el corpus dorado).

    Los programas de declinación honesta del modelo (`{"unsupported": …}`) y los que no
    traen `parts` no se tocan: no hay material que validar.
    """
    partes = programa.get("parts")
    if dsl.is_decline(programa) or not isinstance(partes, list):
        return
    for parte in partes:
        if not isinstance(parte, dict) or "material" not in parte:
            continue
        pedido = parte.get("material")
        try:
            canonico = materiales.normalizar(pedido)
        except materiales.ErrorMateriales as exc:
            # Una tabla ilegible es un error de configuración, no del usuario.
            raise ErrorPipeline(str(exc)) from exc
        if canonico is None:
            nombre = _material_pedido(pedido)
            soportados = ", ".join(materiales.SOPORTADOS)
            if nombre is None:
                raise _declinar(
                    declinacion.Causa.MATERIAL_NO_SOPORTADO,
                    f"la pieza «{parte.get('id')}» no indica un material válido; "
                    f"materiales soportados: {soportados}",
                )
            raise _declinar(
                declinacion.Causa.MATERIAL_NO_SOPORTADO,
                f"el material «{nombre}» no está entre los materiales soportados ({soportados})",
            )
        parte["material"] = canonico


def verificar_programa(programa: dict) -> dict:
    """Valida el programa con el verificador de constraint-kit (AC1).

    Devuelve el informe del verificador si pasa sin errores; lanza
    PiezaDeclinada ante una declinación y ErrorVerificacion ante errores. Antes de
    verificar, el guard de material deja el material canónico o declina (HU-48, RF-5).
    """
    validar_materiales(programa)
    informe = dsl.check(programa)
    if informe["declined"]:
        raise _declinar(declinacion.causa_de_informe(informe), detalle=informe["reason"])
    if not informe["ok"] or informe["n_errors"]:
        errores = [
            diagnostico["message"]
            for diagnostico in informe["diagnostics"]
            if diagnostico.get("severity") == "error"
        ]
        raise ErrorVerificacion(
            "; ".join(errores) or "programa inválido",
            causa=declinacion.causa_de_informe(informe),
        )
    logger.info("pipeline: programa verificado")
    return informe


def validar_catalogo(programa: dict) -> None:
    """Declina lo que no es una pieza única del catálogo (HU-05, AC1).

    Las declinaciones del modelo y los programas mal formados se dejan al
    verificador de constraint-kit, que da el diagnóstico correspondiente.
    """
    partes = programa.get("parts")
    if dsl.is_decline(programa) or not isinstance(partes, list):
        return
    if "defs" in programa or len(partes) > 1:
        raise _declinar(
            declinacion.Causa.FAMILIA_NO_SOPORTADA,
            "los ensamblajes de varias piezas están fuera del alcance",
        )
    tipos = [parte.get("type") for parte in partes if isinstance(parte, dict)]
    ajenos = [tipo for tipo in tipos if tipo not in CATALOGO]
    if ajenos:
        # El nombre del tipo del motor es un identificador interno: no se muestra (AC2).
        raise _declinar(declinacion.Causa.FAMILIA_NO_SOPORTADA, detalle=str(ajenos[0]))


def _codificar_cadena_step(texto: str) -> str:
    """Codifica una cadena para STEP (ISO 10303-21): no ASCII como \\X2\\hhhh\\X0\\."""
    salida = []
    for caracter in texto.replace("'", "''"):
        if caracter == "\\":
            salida.append("\\\\")
        elif ord(caracter) < 128:
            salida.append(caracter)
        else:
            salida.append(f"\\X2\\{ord(caracter):04X}\\X0\\")
    return "".join(salida)


def marcar_step(ruta: Path) -> None:
    """Escribe la marca de diseño preliminar en FILE_DESCRIPTION del STEP (AC3)."""
    contenido = ruta.read_text(encoding="ascii")
    cabecera, separador, datos = contenido.partition("ENDSEC;")
    marcada, reemplazos = re.subn(
        r"FILE_DESCRIPTION\(\(.*?\),",
        lambda _: f"FILE_DESCRIPTION(('{_codificar_cadena_step(MARCA_PRELIMINAR)}'),",
        cabecera,
        count=1,
        flags=re.S,
    )
    if not reemplazos:
        raise ErrorPipeline("El STEP exportado no tiene FILE_DESCRIPTION para la marca.")
    ruta.write_text(marcada + separador + datos, encoding="ascii")


def _resumen_materiales(partes: list[dict]) -> dict[tuple[str, str], dict[str, float]]:
    """Agrupa el reporte del build por tipo y material para el BOM (RF-2, AC2).

    `builder.build_assembly` ya pesa cada parte con la densidad de su material
    (`DENSITY_G_MM3`), así que el costo sale de esa masa sin recalcular geometría. El
    material faltante cuenta como `steel`, que es el valor por defecto del kit.
    """
    filas: dict[tuple[str, str], dict[str, float]] = {}
    for parte in partes:
        material = str(parte.get("material") or "steel").strip().lower()
        fila = filas.setdefault((str(parte["type"]), material), {"qty": 0.0, "mass_g": 0.0})
        fila["qty"] += 1
        fila["mass_g"] += float(parte.get("mass_g") or 0.0)
    return filas


def _csv_materiales(filas: dict[tuple[str, str], dict[str, float]]) -> str:
    """Arma el CSV del BOM con material, masa y costo estimado (RF-3, RNF-3).

    Extiende las cuatro columnas históricas al final para no romper a quien las lee; el
    total conserva `TOTAL`, la cantidad de piezas y la masa en sus primeras posiciones.
    """
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(COLUMNAS_BOM)
    piezas = 0
    masa_total = 0.0
    costo_total = 0.0
    for tipo, material in sorted(filas):
        fila = filas[(tipo, material)]
        cantidad = int(fila["qty"])
        masa = fila["mass_g"]
        unitaria = masa / cantidad if cantidad else 0.0
        try:
            precio_g = materiales.precio_usd_g(material)
        except materiales.ErrorMateriales as exc:
            raise ErrorPipeline(str(exc)) from exc
        # Convención de factura: el unitario se redondea y la línea sale de él, así la
        # fila cuadra con `unitario × cantidad`; el total suma las líneas ya redondeadas.
        costo_unitario = round(unitaria * precio_g, 2)
        costo_linea = round(costo_unitario * cantidad, 2)
        escritor.writerow(
            [
                tipo,
                cantidad,
                round(masa, 3),
                round(unitaria, 3),
                material,
                f"{costo_unitario:.2f}",
                f"{costo_linea:.2f}",
            ]
        )
        piezas += cantidad
        masa_total += masa
        costo_total += costo_linea
    escritor.writerow([])
    escritor.writerow(
        ["TOTAL", piezas, round(masa_total, 3), "", "", "", f"{round(costo_total, 2):.2f}"]
    )
    return salida.getvalue()


def construir_pieza(
    programa: dict, directorio: Path, *, solicitud_id: str | None = None
) -> ResultadoPieza:
    """Verifica, construye y exporta STEP, GLB y CSV en `directorio` (AC1-AC4)."""
    verificar_programa(programa)

    inicio = time.perf_counter()
    ensamble, partes = builder.build_assembly(programa)
    # La caja se mide antes de exportar: builder.export triangula la pieza para
    # el GLB y la caja de OpenCascade posterior suma el margen de la malla
    # (+2,74 mm por eje en un loft), lo que falsea el AC3 en piezas curvas.
    caja = ensamble.toCompound().BoundingBox()
    base = Path(directorio) / NOMBRE_PIEZA
    # El BOM se calcula antes de exportar: un precio faltante no deja STEP ni GLB a medias.
    csv_bom = _csv_materiales(_resumen_materiales(partes))
    exportado = builder.export(ensamble, str(base))
    marcar_step(Path(exportado["step"]))
    bom_csv = base.with_suffix(".csv")
    bom_csv.write_text(csv_bom, encoding="utf-8", newline="")
    firma = dsl.signature(ensamble)
    duracion = time.perf_counter() - inicio

    resultado_t = ResultadoPieza(
        programa=programa,
        step=Path(exportado["step"]),
        glb=Path(exportado["glb"]),
        bom_csv=bom_csv,
        volumen_mm3=float(firma["volume"]),
        caja_mm=(round(caja.xlen, 2), round(caja.ylen, 2), round(caja.zlen, 2)),
        tiempo_construccion_s=duracion,
        familia=familia_de_programa(programa),
        programa_json=Path(directorio) / "programa.json",
        firma=firma,
        dxf=Path(directorio) / f"{NOMBRE_PIEZA}.dxf",
        pdf=Path(directorio) / f"{NOMBRE_PIEZA}.pdf",
        partes=list(partes),
    )
    plano_dxf.escribir(resultado_t, resultado_t.dxf)
    # SPEC-044 AC2: el cajetín del PDF lleva el id real de la solicitud; si quien
    # invoca no lo pasa, se toma el del contexto de ejecución (SSE y worker lo
    # fijan con `contexto_solicitud`), y sin ninguno conserva el valor neutro.
    plano_pdf.escribir(
        resultado_t,
        resultado_t.pdf,
        solicitud_id=solicitud_id or job_id_actual() or "—",
    )
    return resultado_t


def familia_de_programa(programa: dict) -> str:
    """Familia del catálogo según los tipos de pieza del programa (HU-16, AC2)."""
    partes = programa.get("parts")
    if not isinstance(partes, list):
        return "desconocida"
    tipos = {
        str(parte["type"]) for parte in partes if isinstance(parte, dict) and parte.get("type")
    }
    if len(tipos) == 1:
        return next(iter(tipos))
    return "ensamblaje" if tipos else "desconocida"


def planificar_con_llm(texto: str) -> dict:
    """Pide al modelo (DeepSeek por defecto, HU-14) el programa constraint-kit de la pieza.

    Por defecto consulta https://api.deepseek.com con DEEPSEEK_API_KEY;
    LLM_BASE_URL apunta a otro servidor compatible con OpenAI y LLM_MODEL
    cambia el modelo. La API key nunca forma parte de los mensajes de error.
    """
    return _programa_de(_respuesta_modelo(texto))


def _planificador_con_uso(
    medir_uso: Callable[[dict], None] | None,
    control: ControlGeneracion | None = None,
) -> Callable[[str], dict]:
    """Planificador por defecto que informa el `usage` del proveedor (HU-16, AC2)."""
    return _planificador(medir_uso, control)


def _planificador_edicion(
    programa_previo: dict,
    medir_uso: Callable[[dict], None] | None = None,
    control: ControlGeneracion | None = None,
) -> Callable[[str], dict]:
    """Planificador de una edición: prompt de edición y programa previo (HU-35)."""
    return _planificador(
        medir_uso,
        control,
        sistema=PROMPT_EDICION.texto,
        componer=lambda instruccion: _mensaje_edicion(programa_previo, instruccion),
    )


def _planificador(
    medir_uso: Callable[[dict], None] | None,
    control: ControlGeneracion | None,
    *,
    sistema: str | None = None,
    componer: Callable[[str], str] | None = None,
) -> Callable[[str], dict]:
    """Planificador que devuelve el programa e informa el `usage` del proveedor.

    `sistema` elige el prompt de sistema (`PROMPT_SISTEMA` si es `None`) y
    `componer` arma el mensaje de usuario a partir del texto recibido.
    """

    def planificar(texto: str) -> dict:
        mensaje = componer(texto) if componer is not None else texto
        llm_resiliente.reiniciar_metricas()
        try:
            respuesta = _respuesta_modelo(mensaje, control=control, sistema=sistema)
        except Exception:
            if medir_uso is not None:
                medir_uso(llm_resiliente.metricas_actuales())
            raise
        if medir_uso is not None:
            medir_uso(
                {
                    **(respuesta.get("usage") or {}),
                    **llm_resiliente.metricas_actuales(),
                }
            )
        return _programa_de(respuesta)

    return planificar


def _mensaje_edicion(programa_previo: dict, instruccion: str) -> str:
    """Mensaje de usuario de una edición: programa vigente e instrucción delimitada."""
    return (
        "Programa constraint-kit vigente de la pieza (JSON):\n"
        f"{json.dumps(programa_previo, ensure_ascii=False, sort_keys=True)}\n\n"
        "Instrucción de cambio (en español):\n"
        f"«{instruccion}»\n\n"
        "Devuelve el programa completo con solo ese cambio aplicado."
    )


def _programa_de(respuesta: dict) -> dict:
    """Extrae el programa del cuerpo de respuesta del proveedor."""
    version = respuesta.get("model") or llm.planner_model()
    try:
        contenido = respuesta["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        error = ErrorGeneracion("Respuesta del modelo sin contenido.")
        error.version_modelo = version
        raise error from exc
    try:
        if not isinstance(contenido, str):
            raise ErrorGeneracion("Respuesta del modelo sin contenido de texto.")
        programa = ProgramaLLM(extraer_programa(contenido))
    except Exception as exc:
        exc.version_modelo = version
        raise
    programa.version_modelo = version
    return programa


def cuerpo_planificador(texto: str, *, sistema: str | None = None) -> dict:
    """Cuerpo exacto de la petición del planificador (HU-44, SPEC-045).

    Lo usan `_respuesta_modelo` y el replay del banco para derivar la misma clave
    canónica de HU-25: prompt vigente, solicitud en español, modelo, temperatura y
    formato de respuesta. Nunca incluye credenciales.
    """
    return {
        "model": llm.planner_model(),
        "messages": [
            {"role": "system", "content": PROMPT_SISTEMA if sistema is None else sistema},
            {"role": "user", "content": texto},
        ],
        "temperature": TEMPERATURA_LLM,
        "response_format": {"type": "json_object"},
    }


def _respuesta_modelo(
    texto: str,
    *,
    control: ControlGeneracion | None = None,
    sistema: str | None = None,
) -> dict:
    """Llama al modelo servido con el prompt del sistema y la solicitud.

    `control` permite detener los reintentos si el trabajo SSE se cancela y
    `sistema` elige el prompt del sistema (el del planificador si es `None`).
    """
    url = llm.base_url("planner")
    con_clave = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if "api.deepseek.com" in url and not con_clave:
        raise ModeloNoDisponible("El modelo no está configurado: falta DEEPSEEK_API_KEY.")

    cuerpo = cuerpo_planificador(texto, sistema=sistema)
    try:
        return llm_resiliente.consultar(
            cuerpo,
            url=url,
            timeout=TIEMPO_ESPERA_LLM,
            proveedor=llm.chat,
            cancelado=control.comprobar_cancelacion if control is not None else None,
            validador=_programa_de,
        )
    except llm_resiliente.ConfiguracionInvalida as exc:
        raise ModeloNoDisponible(f"La configuración del LLM es inválida: {exc}") from exc
    except httpx.TimeoutException as exc:
        raise ModeloNoDisponible(
            f"El modelo no respondió dentro del plazo total de {TIEMPO_ESPERA_LLM:.0f} s."
        ) from exc
    except httpx.HTTPStatusError as exc:
        codigo = exc.response.status_code
        # AC3: el cuerpo del proveedor puede incluir la cabecera Authorization;
        # se registra ya redactado y nunca se propaga al mensaje HTTP.
        logger.warning("proveedor respondió HTTP %s: %s", codigo, redactar(exc.response.text))
        mensaje = MENSAJES_HTTP.get(codigo, f"El modelo respondió con error HTTP {codigo}.")
        raise ModeloNoDisponible(mensaje) from exc
    except httpx.HTTPError as exc:  # conexión caída u otro fallo de transporte
        raise ModeloNoDisponible("No fue posible conectar con el modelo.") from exc


def _construir_programa(
    programa: dict,
    directorio: Path,
    *,
    version: str,
    tiempo_generacion: float,
    control: ControlGeneracion | None,
    solicitud_id: str | None = None,
) -> ResultadoPieza:
    """Escribe `programa.json`, valida el catálogo y construye la pieza (AC1-AC5).

    Camino común de una generación inicial y de una edición (HU-35): siempre en un
    directorio nuevo, con la misma sanitización del artefacto, la misma declinación
    con causa de SPEC-027 y la misma verificación determinista.
    """
    salida = Path(directorio) / uuid.uuid4().hex
    salida.mkdir(parents=True, exist_ok=True)
    programa_json = salida / "programa.json"
    # AC5 (HU-16): el artefacto pasa por la misma sanitización que el registro; el
    # programa en memoria sigue intacto para construir la pieza.
    programa_json.write_text(
        _sanitizar(json.dumps(programa, ensure_ascii=False, indent=2)), encoding="utf-8"
    )

    try:
        validar_catalogo(programa)
    except PiezaDeclinada as exc:
        logger.info("pipeline: pieza declinada")
        exc.programa_json = programa_json
        exc.version_modelo = version
        raise
    logger.info("pipeline: catálogo validado")

    if control is not None:
        control.comprobar_cancelacion()

    try:
        # El id sólo viaja cuando lo hay: el contexto de ejecución cubre los
        # flujos SSE y worker, y los dobles de prueba con la firma histórica
        # no reciben una kw que no esperan (SPEC-044 AC2).
        if solicitud_id:
            resultado = construir_pieza(programa, salida, solicitud_id=solicitud_id)
        else:
            resultado = construir_pieza(programa, salida)
    except Exception as exc:
        exc.version_modelo = version
        if isinstance(exc, PiezaDeclinada):
            logger.info("pipeline: pieza declinada")
            exc.programa_json = programa_json
        else:
            logger.warning("pipeline: fallo al construir (%s)", type(exc).__name__)
        raise
    if control is not None:
        control.comprobar_cancelacion()
    logger.info("pipeline: pieza construida (%s)", resultado.familia)
    return ResultadoPieza(
        programa=resultado.programa,
        step=resultado.step,
        glb=resultado.glb,
        bom_csv=resultado.bom_csv,
        volumen_mm3=resultado.volumen_mm3,
        caja_mm=resultado.caja_mm,
        tiempo_construccion_s=resultado.tiempo_construccion_s,
        tiempo_generacion_s=tiempo_generacion,
        familia=resultado.familia,
        programa_json=programa_json,
        version_modelo=version,
        dxf=resultado.dxf,
        pdf=resultado.pdf,
        partes=resultado.partes,
        # HU-49 (AC3): la firma geométrica viaja hasta la API. El DXF no se propaga
        # aquí a propósito: `/generar` conserva su cuerpo de respuesta (HU-35, RNF-2).
        firma=resultado.firma,
    )


def construir_desde_programa(programa: dict, *, directorio: Path = RUTA_SALIDA) -> ResultadoPieza:
    """Construye una pieza a partir de un programa DSL ya armado, sin el modelo (HU-49).

    Especificación: specs/050-hu-49-plantillas-parametrizadas/spec.md
    - RF-2 (S2): el programa de una plantilla pasa por el mismo camino que el de una
      generación por texto (`validar_catalogo`, verificación determinista, exportación).
    - RNF-1 (S6): no consulta al LLM, así que no gasta tokens; el tiempo de generación
      es cero.
    """
    return _construir_programa(
        programa,
        directorio,
        version="plantilla",
        tiempo_generacion=0.0,
        control=None,
    )


def generar_pieza(
    texto: str,
    *,
    planificar: Callable[[str], dict] | None = None,
    directorio: Path = RUTA_SALIDA,
    control: ControlGeneracion | None = None,
    medir_uso: Callable[[dict], None] | None = None,
    solicitud_id: str | None = None,
) -> ResultadoPieza:
    """Genera el programa desde el texto en español y construye la pieza (AC1-AC5).

    Cada solicitud escribe en su propia subcarpeta de `directorio`, con
    `programa.json` en cuanto el modelo entrega un programa y los entregables
    cuando la pieza se construye. `medir_uso` recibe el `usage` del proveedor
    para el seguimiento (HU-16); sin él el comportamiento es el de siempre.
    """
    logger.info("pipeline: validando solicitud")
    if control is not None:
        control.informar("validando")
    if not texto.strip() or len(texto) > 1000:
        raise ValueError("La descripción debe contener entre 1 y 1000 caracteres.")
    inicio = time.perf_counter()
    if control is not None:
        control.informar("generando")
    if planificar is None:
        planificar = _planificador_con_uso(medir_uso, control)
    logger.info("pipeline: generando programa")
    try:
        programa = planificar(texto)
    except Exception as exc:
        if not hasattr(exc, "version_modelo"):
            exc.version_modelo = os.getenv("LLM_MODEL_VERSION") or llm.planner_model()
        raise
    logger.info("pipeline: programa generado")
    version = getattr(programa, "version_modelo", None) or llm.planner_model()
    if control is not None:
        control.comprobar_cancelacion()
    tiempo_generacion = time.perf_counter() - inicio
    return _construir_programa(
        programa,
        directorio,
        version=version,
        tiempo_generacion=tiempo_generacion,
        control=control,
        solicitud_id=solicitud_id,
    )


def editar_pieza(
    programa_previo: dict,
    instruccion: str,
    *,
    planificar: Callable[[str], dict] | None = None,
    directorio: Path = RUTA_SALIDA,
    control: ControlGeneracion | None = None,
    medir_uso: Callable[[dict], None] | None = None,
    solicitud_id: str | None = None,
) -> ResultadoPieza:
    """Aplica una instrucción de cambio al programa vigente y construye la pieza (HU-35).

    Especificación: specs/036-hu-35-edicion-iterativa/spec.md
    - RF-1 (S1): la instrucción llega al modelo de edición con el programa previo.
    - RF-3 (S3): el programa nuevo pasa por la misma verificación determinista que
      una generación inicial, en un directorio nuevo.
    - RF-6 (S6): si la edición rompe la verificación, se declina con la causa de
      SPEC-027 y no se construye nada, así que la versión anterior queda intacta.

    `medir_uso` recibe el `usage` del proveedor para el seguimiento (HU-16).
    """
    logger.info("pipeline: validando instrucción de edición")
    if control is not None:
        control.informar("validando")
    if not instruccion.strip() or len(instruccion) > 1000:
        raise ValueError("La instrucción de cambio debe contener entre 1 y 1000 caracteres.")
    inicio = time.perf_counter()
    if control is not None:
        control.informar("generando")
    if planificar is None:
        planificar = _planificador_edicion(programa_previo, medir_uso, control)
    logger.info("pipeline: editando programa")
    try:
        programa = planificar(instruccion)
    except Exception as exc:
        if not hasattr(exc, "version_modelo"):
            exc.version_modelo = os.getenv("LLM_MODEL_VERSION") or llm.planner_model()
        raise
    logger.info("pipeline: programa editado")
    version = getattr(programa, "version_modelo", None) or llm.planner_model()
    if control is not None:
        control.comprobar_cancelacion()
    tiempo_generacion = time.perf_counter() - inicio
    return _construir_programa(
        programa,
        directorio,
        version=version,
        tiempo_generacion=tiempo_generacion,
        control=control,
        solicitud_id=solicitud_id,
    )
