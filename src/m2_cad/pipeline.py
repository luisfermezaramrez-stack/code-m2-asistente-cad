"""Pipeline de generación y verificación geométrica (HU-04).

Convierte la solicitud traducida en un programa constraint-kit, lo valida
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
from m2_cad.traduccion import traducir_solicitud

RUTA_SALIDA = Path("outputs")
NOMBRE_PIEZA = "pieza"
TIEMPO_ESPERA_LLM = 120.0

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

# Prompt de sistema tomado de vendor/constraint-kit/drivers/dsl_experiment.py
# (traducción de texto en inglés a programa DSL de constraint-kit).
PROMPT_SISTEMA = (
    "Translate a plain-English mechanical-part/assembly description into a "
    "constraint-kit DSL program. "
    'Output ONLY JSON: {"parts":[{"id","type","material","params":{...}}],'
    '"mates":[...]}. '
    "PART TYPES + params (mm): spacer{outer_d,bore_d,height}; "
    "spur_gear{module,teeth,width,bore_d}; "
    "plate{width,depth,thick,boss_d,boss_h,bolt_d,bolt_circle,bolt_count}; "
    "shaft{diameter,length}; washer{outer_d,bore_d,thick}; nut{af,height,bore_d}; "
    "bolt{shank_d,length,head_d,head_h}; panel{width,depth,height}; "
    "link{length,width,thickness}; housing{width,depth,height,wall,bore_d}; "
    "sheet_bracket{thickness,base_length,flange_length,width}. "
    'MATES connect parts; use either {"a","b","intent"} with intent in '
    '[seat_on,insert,fasten,mesh], OR {"a","a_joint","b","b_joint","type"} with '
    "type in [coincident,rigid,contact,mesh,revolute]. plate anchors: "
    "mount,bolt0..N. spur_gear: bore_base,bore_top. spacer: top,bottom. "
    "The FIRST part is the fixed base. "
    "HONESTY RULE: if the description needs a part type or feature you have NO "
    "match for (synchronizer, helical/bevel/worm gear, spline, "
    "tapered/roller/needle bearing, shift fork, threads-as-feature), do NOT "
    'substitute a different part — output exactly {"unsupported":"<what you '
    'cannot express>"}. '
    "Output JSON only, no prose."
)


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
    traduccion: str = ""

    def a_respuesta(self) -> dict[str, str]:
        """Serializa el resultado para la API (todos los valores como texto)."""
        return {
            "step": str(self.step),
            "glb": str(self.glb),
            "bom_csv": str(self.bom_csv),
            "traduccion": self.traduccion,
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
    )


def planificar_con_llm(texto_en: str) -> dict:
    """Pide al modelo servido (HU-01) el programa constraint-kit de la pieza."""
    url = os.environ.get("LLM_BASE_URL")
    if not url:
        raise ModeloNoDisponible("LLM_BASE_URL no está configurada.")

    cuerpo = {
        "model": llm.planner_model(),
        "messages": [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": texto_en},
        ],
        "temperature": 0.1,
    }
    try:
        respuesta = llm.chat(cuerpo, url=url, timeout=TIEMPO_ESPERA_LLM)
    except httpx.HTTPError as exc:  # tiempo de espera, conexión o estado HTTP
        raise ModeloNoDisponible(f"El modelo no respondió: {exc}") from exc
    try:
        contenido = respuesta["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ErrorGeneracion("Respuesta del modelo sin contenido.") from exc
    return extraer_programa(contenido)


def generar_pieza(
    texto: str,
    *,
    traducir: Callable[[str], str] = traducir_solicitud,
    planificar: Callable[[str], dict] = planificar_con_llm,
    directorio: Path = RUTA_SALIDA,
) -> ResultadoPieza:
    """Traduce, genera el programa y construye la pieza (AC1-AC5).

    Cada solicitud escribe en su propia subcarpeta de `directorio`.
    """
    inicio = time.perf_counter()
    traduccion = traducir(texto)
    programa = planificar(traduccion)
    tiempo_generacion = time.perf_counter() - inicio

    validar_catalogo(programa)

    resultado = construir_pieza(programa, Path(directorio) / uuid.uuid4().hex)
    return ResultadoPieza(
        programa=resultado.programa,
        step=resultado.step,
        glb=resultado.glb,
        bom_csv=resultado.bom_csv,
        volumen_mm3=resultado.volumen_mm3,
        caja_mm=resultado.caja_mm,
        tiempo_construccion_s=resultado.tiempo_construccion_s,
        tiempo_generacion_s=tiempo_generacion,
        traduccion=traduccion,
    )
