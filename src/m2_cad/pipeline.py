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

import json
import os
import re
import time
import uuid
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx
from constraint_kit import bom, builder, dsl, llm

from m2_cad import MARCA_PRELIMINAR
from m2_cad.registro import _sanitizar

RUTA_SALIDA = Path("outputs")
NOMBRE_PIEZA = "pieza"
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
PREFIJO_DECLINACION = "El asistente no puede construir esta pieza:"

# Prompt de sistema para DeepSeek (HU-14): el modelo no está afinado para el DSL
# de constraint-kit, así que el prompt describe los parámetros de cada tipo del
# catálogo (firmas de constraint_kit/parts.py y parts_bd.py, ejemplos del banco
# HU-02) y recibe la solicitud en español, sin traducción previa.
PROMPT_SISTEMA = (
    "You are a CAD planner. Convert a mechanical-part description, usually written in "
    "Spanish (sometimes English), into a constraint-kit DSL program for ONE single part. "
    'Output ONLY a JSON object: {"parts":[{"id":"p","type":"<type>","material":"steel",'
    '"params":{...}}],"mates":[]}. '
    "Copy every number from the description exactly; all lengths are in mm; a Spanish "
    "decimal comma (12,5) means 12.5. Use 0 for optional features the description does "
    "not ask for. material is one of steel, stainless, aluminum, brass, copper, abs, pla, "
    "nylon (default steel). "
    "PART TYPES + params: "
    "plate{width,depth,thick,boss_d,boss_h,bolt_d,bolt_circle,bolt_count}: rectangular "
    "plate centered on the origin, width along X, depth along Y, thick along Z, optional "
    "centered top boss and a circle of bolt_count through holes of diameter bolt_d. "
    "sheet_bracket{thickness,base_length,flange_length,width,bend_radius}: constant-"
    "thickness 90-degree L bracket, base along X, flange rising along Z, width along Y. "
    "adapter{bottom_w,bottom_d,top_d,height}: solid loft from a bottom_w x bottom_d "
    "rectangle at z=0 to a circle of diameter top_d at z=height. "
    'flange{nps,flange_class,kind}: ASME B16.5 pipe flange, nps is a string ("1","2"), '
    "flange_class an integer (150, 300, ...), kind one of weld_neck, slip_on, blind. "
    "spacer{outer_d,bore_d,height}: cylindrical spacer with a coaxial through bore "
    "(bore_d 0 means solid). "
    'screw{size,length,simple,fastener_type}: ISO 4762 socket-head cap screw, size "M<d>-'
    '<pitch>" (e.g. "M5-0.8"), length in mm, simple true, fastener_type "iso4762". '
    'extrusion{rail_size,length}: aluminum V-slot profile along Z, rail_size one of "20x20",'
    '"20x40","20x60","20x80","40x40". '
    "pipe{nps,length,material,identifier}: straight standard pipe along Z, nps a string, "
    'material "steel", identifier the schedule (e.g. "40"). '
    "HONESTY RULE: if the description needs several parts (an assembly) or a part type or "
    "feature not listed above (gears, bearings, springs, threads-as-feature, ...), do NOT "
    'substitute a different part; output exactly {"unsupported":"<what you cannot '
    'express>"}. '
    "Output json only, no prose."
)

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
    """La salida del modelo no contiene un programa interpretable."""


class ErrorVerificacion(ErrorPipeline):
    """El programa no pasa el verificador de constraint-kit (AC1)."""


class PiezaDeclinada(ErrorPipeline):
    """La pieza no se construye; `motivo` es legible en español (HU-05, AC1)."""

    def __init__(self, motivo: str, detalle: str | None = None) -> None:
        super().__init__(f"Pieza declinada: {motivo}")
        self.motivo = motivo
        self.detalle = detalle
        # Programa que originó la declinación, para el seguimiento (HU-16, AC2).
        self.programa_json: Path | None = None


def _declinar(explicacion: str, detalle: str | None = None) -> PiezaDeclinada:
    catalogo = ", ".join(CATALOGO.values())
    return PiezaDeclinada(
        f"{PREFIJO_DECLINACION} {explicacion} Solo se generan piezas únicas del catálogo: "
        f"{catalogo}.",
        detalle,
    )


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

    def a_respuesta(self) -> dict[str, str]:
        """Serializa el resultado para la API (todos los valores como texto)."""
        return {
            "step": str(self.step),
            "glb": str(self.glb),
            "bom_csv": str(self.bom_csv),
            "aviso": MARCA_PRELIMINAR,
            "volumen_mm3": f"{self.volumen_mm3:.2f}",
            "caja_mm": "x".join(f"{lado:.2f}" for lado in self.caja_mm),
            "tiempo_generacion_s": f"{self.tiempo_generacion_s:.3f}",
            "tiempo_construccion_s": f"{self.tiempo_construccion_s:.3f}",
        }


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


def verificar_programa(programa: dict) -> dict:
    """Valida el programa con el verificador de constraint-kit (AC1).

    Devuelve el informe del verificador si pasa sin errores; lanza
    PiezaDeclinada ante una declinación y ErrorVerificacion ante errores.
    """
    informe = dsl.check(programa)
    if informe["declined"]:
        detalle = informe["reason"] or "sin detalle"
        raise _declinar(
            f"la solicitud está fuera del catálogo (el modelo indicó: «{detalle}»).", detalle
        )
    if not informe["ok"] or informe["n_errors"]:
        errores = [
            diagnostico["message"]
            for diagnostico in informe["diagnostics"]
            if diagnostico.get("severity") == "error"
        ]
        raise ErrorVerificacion("; ".join(errores) or "programa inválido")
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
        raise _declinar("los ensamblajes de varias piezas están fuera del alcance.")
    tipos = [parte.get("type") for parte in partes if isinstance(parte, dict)]
    ajenos = [tipo for tipo in tipos if tipo not in CATALOGO]
    if ajenos:
        raise _declinar(f"el tipo de pieza «{ajenos[0]}» está fuera del catálogo.", ajenos[0])


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


def _resumen_materiales(partes: list[dict]) -> dict:
    """Arma el resumen que bom.bom_document espera a partir del reporte."""
    masa_por_tipo: dict[str, float] = defaultdict(float)
    for parte in partes:
        masa_por_tipo[parte["type"]] += parte.get("mass_g") or 0.0
    return {
        "bom": dict(Counter(parte["type"] for parte in partes)),
        "mass_by_type": dict(masa_por_tipo),
        "mass_g": sum(masa_por_tipo.values()),
        "part_count": len(partes),
    }


def construir_pieza(programa: dict, directorio: Path) -> ResultadoPieza:
    """Verifica, construye y exporta STEP, GLB y CSV en `directorio` (AC1-AC4)."""
    verificar_programa(programa)

    inicio = time.perf_counter()
    ensamble, partes = builder.build_assembly(programa)
    # La caja se mide antes de exportar: builder.export triangula la pieza para
    # el GLB y la caja de OpenCascade posterior suma el margen de la malla
    # (+2,74 mm por eje en un loft), lo que falsea el AC3 en piezas curvas.
    caja = ensamble.toCompound().BoundingBox()
    base = Path(directorio) / NOMBRE_PIEZA
    exportado = builder.export(ensamble, str(base))
    marcar_step(Path(exportado["step"]))
    bom_csv = base.with_suffix(".csv")
    bom_csv.write_text(bom.bom_document(_resumen_materiales(partes), fmt="csv"), encoding="utf-8")
    firma = dsl.signature(ensamble)
    duracion = time.perf_counter() - inicio

    return ResultadoPieza(
        programa=programa,
        step=Path(exportado["step"]),
        glb=Path(exportado["glb"]),
        bom_csv=bom_csv,
        volumen_mm3=float(firma["volume"]),
        caja_mm=(round(caja.xlen, 2), round(caja.ylen, 2), round(caja.zlen, 2)),
        tiempo_construccion_s=duracion,
        familia=familia_de_programa(programa),
        programa_json=Path(directorio) / "programa.json",
    )


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


def _planificador_con_uso(medir_uso: Callable[[dict], None] | None) -> Callable[[str], dict]:
    """Planificador por defecto que informa el `usage` del proveedor (HU-16, AC2)."""

    def planificar(texto: str) -> dict:
        respuesta = _respuesta_modelo(texto)
        if medir_uso is not None:
            medir_uso(respuesta.get("usage") or {})
        return _programa_de(respuesta)

    return planificar


def _programa_de(respuesta: dict) -> dict:
    """Extrae el programa del cuerpo de respuesta del proveedor."""
    try:
        contenido = respuesta["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ErrorGeneracion("Respuesta del modelo sin contenido.") from exc
    return extraer_programa(contenido)


def _respuesta_modelo(texto: str) -> dict:
    """Llama al modelo servido con el prompt del sistema y la solicitud."""
    url = llm.base_url("planner")
    con_clave = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if "api.deepseek.com" in url and not con_clave:
        raise ModeloNoDisponible("El modelo no está configurado: falta DEEPSEEK_API_KEY.")

    cuerpo = {
        "model": llm.planner_model(),
        "messages": [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": texto},
        ],
        "temperature": TEMPERATURA_LLM,
        "response_format": {"type": "json_object"},
    }
    try:
        return llm.chat(cuerpo, url=url, timeout=TIEMPO_ESPERA_LLM)
    except httpx.TimeoutException as exc:
        raise ModeloNoDisponible(
            f"El modelo no respondió a tiempo (más de {TIEMPO_ESPERA_LLM:.0f} s)."
        ) from exc
    except httpx.HTTPStatusError as exc:
        codigo = exc.response.status_code
        mensaje = MENSAJES_HTTP.get(codigo, f"El modelo respondió con error HTTP {codigo}.")
        raise ModeloNoDisponible(mensaje) from exc
    except httpx.HTTPError as exc:  # conexión caída u otro fallo de transporte
        raise ModeloNoDisponible("No fue posible conectar con el modelo.") from exc


def generar_pieza(
    texto: str,
    *,
    planificar: Callable[[str], dict] | None = None,
    directorio: Path = RUTA_SALIDA,
    medir_uso: Callable[[dict], None] | None = None,
) -> ResultadoPieza:
    """Genera el programa desde el texto en español y construye la pieza (AC1-AC5).

    Cada solicitud escribe en su propia subcarpeta de `directorio`, con
    `programa.json` en cuanto el modelo entrega un programa y los entregables
    cuando la pieza se construye. `medir_uso` recibe el `usage` del proveedor
    para el seguimiento (HU-16); sin él el comportamiento es el de siempre.
    """
    inicio = time.perf_counter()
    if planificar is None:
        planificar = _planificador_con_uso(medir_uso)
    programa = planificar(texto)
    tiempo_generacion = time.perf_counter() - inicio

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
        exc.programa_json = programa_json
        raise

    resultado = construir_pieza(programa, salida)
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
    )
