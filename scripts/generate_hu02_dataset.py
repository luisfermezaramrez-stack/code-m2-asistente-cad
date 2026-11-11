"""Mide los 30 positivos HU-02; solo --write permite reemplazar el CSV."""

import argparse
import csv
import importlib
import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from m2_cad.dataset import (
    COLUMNS,
    DEFAULT_PATH,
    analytical_reference,
    compare_reference,
    json_object,
    read_dataset,
    validate_dataset,
)

ROOT = Path(__file__).resolve().parents[1]
ENGINE_REVISION = "2ed27db4d8fa821afef41103f0efc9befbf116e6"
VERSIONS = {
    "constraint-kit": "0.1.0",
    "cadquery": "2.7.0",
    "cadquery-ocp": "7.8.1.1.post1",
    "build123d": "0.10.0",
    "bd-warehouse": "0.2.0",
}
NEGATIVES = (
    (
        "Calcula y certifica la resistencia estructural de una viga de acero para una cubierta; "
        "no solicito generar una pieza CAD.",
        "El cálculo y la certificación estructural están fuera del alcance.",
    ),
    (
        "Verifica y certifica el cumplimiento de la NSR-10 de una estructura metálica existente.",
        "La verificación y certificación NSR-10 están fuera del alcance.",
    ),
    (
        "Emite un certificado de cumplimiento RETIE para una instalación eléctrica.",
        "La verificación y certificación RETIE están fuera del alcance.",
    ),
    (
        "Genera un modelo BIM de un edificio y entrégalo en formato nativo de Revit.",
        "La generación Revit/BIM está fuera del alcance.",
    ),
    (
        "Quiero cargar una fotografía para reconstruir automáticamente una pieza, "
        "sin describir su geometría ni aportar medidas textuales.",
        "La entrada por imagen y la reconstrucción desde fotografías están fuera del alcance.",
    ),
    (
        "Diseña y entrega un ensamblaje articulado completo de varias piezas con sus uniones "
        "y movimiento; no lo sustituyas por una pieza única.",
        "Los ensamblajes de varias piezas están fuera del alcance del producto.",
    ),
    (
        "Reentrena el modelo de lenguaje con mis ejemplos de taller y entrega los nuevos pesos.",
        "El reentrenamiento del modelo está fuera del alcance.",
    ),
    (
        "Crea cuentas de usuario con inicio de sesión y permisos para proteger el asistente.",
        "La autenticación y gestión de usuarios están fuera del alcance.",
    ),
    (
        "Procesa simultáneamente solicitudes CAD de múltiples usuarios "
        "con gestión de concurrencia.",
        "La concurrencia de solicitudes está fuera del alcance.",
    ),
    (
        "Realiza un análisis por elementos finitos y certifica las deformaciones "
        "de una estructura; "
        "no quiero únicamente una verificación geométrica.",
        "El análisis estructural y la certificación de deformaciones están fuera del alcance.",
    ),
)


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def specifications():
    """Parámetros fuente explícitos y textos en español, independientes de las referencias."""
    cases = []

    def add(family, engine_type, params, request):
        cases.append(
            {
                "id": f"HU02-P{len(cases) + 1:02d}",
                "familia": family,
                "solicitud": request,
                "medidas": encode(
                    {"unidad": "mm", "tipo_motor": engine_type, "parametros": params}
                ),
            }
        )

    for width, depth, thick, boss_d, boss_h, bolt_d, bolt_circle, bolt_count in (
        (40, 30, 5, 0, 0, 0, 0, 0),
        (60, 50, 6, 0, 0, 4, 30, 4),
        (80, 60, 8, 20, 4, 6, 40, 4),
        (100, 80, 10, 0, 0, 6, 50, 6),
        (120, 100, 6, 24, 5, 5, 70, 8),
    ):
        params = dict(
            width=width,
            depth=depth,
            thick=thick,
            boss_d=boss_d,
            boss_h=boss_h,
            bolt_d=bolt_d,
            bolt_circle=bolt_circle,
            bolt_count=bolt_count,
        )
        boss = (
            f"Resalte cilíndrico centrado sobre la cara superior, diámetro {boss_d} mm "
            f"y altura adicional {boss_h} mm. "
            if boss_d
            else "Sin resalte. "
        )
        holes = (
            f"{bolt_count} agujeros pasantes de diámetro {bolt_d} mm, equiespaciados "
            f"en un círculo de diámetro {bolt_circle} mm centrado en la placa, "
            "primer centro en +X y resto en sentido antihorario visto desde +Z. "
            if bolt_count
            else "Sin agujeros. "
        )
        add(
            "plate",
            "plate",
            params,
            f"Placa rectangular de {width} mm en X, {depth} mm en Y y {thick} mm de espesor "
            "en Z, centrada en el origen. " + boss + holes + "Sin redondeos ni chaflanes.",
        )

    for thickness, base, flange, width in (
        (2, 40, 25, 30),
        (3, 50, 35, 40),
        (4, 60, 40, 45),
        (2.5, 70, 45, 50),
        (5, 80, 60, 60),
    ):
        add(
            "sheet_bracket",
            "sheet_bracket",
            dict(
                thickness=thickness,
                base_length=base,
                flange_length=flange,
                width=width,
                bend_radius=0,
            ),
            f"Escuadra maciza en L a 90 grados, ancho {width} mm en Y, espesor uniforme "
            f"{thickness} mm. La base ocupa X de 0 a {base} mm y Z de 0 a {thickness} mm; "
            f"el ala vertical ocupa X de 0 a {thickness} mm y Z de 0 a {flange} mm. "
            "Centrada en Y, con solapamiento de ambos prismas en la esquina; "
            "radio interior cero, sin taladros ni acabados.",
        )

    for bottom_w, bottom_d, top_d, height in (
        (40, 40, 24, 30),
        (50, 40, 30, 35),
        (60, 50, 32, 40),
        (70, 60, 40, 50),
        (80, 70, 45, 60),
    ):
        add(
            "adapter",
            "adapter",
            dict(bottom_w=bottom_w, bottom_d=bottom_d, top_d=top_d, height=height),
            f"Transición maciza por loft entre un rectángulo de {bottom_w} mm en X por "
            f"{bottom_d} mm en Y, centrado en el plano Z=0 mm, y un círculo de diámetro "
            f"{top_d} mm centrado en el eje Z a altura {height} mm. Sin giro relativo, "
            "sin vaciado, sin taladros y sin acabados.",
        )

    names = {
        "blind": "ciega",
        "slip_on": "deslizante para soldar",
        "weld_neck": "con cuello para soldar",
    }
    for nps, flange_class, kind in (
        ("1", 150, "blind"),
        ("2", 150, "blind"),
        ("1", 150, "slip_on"),
        ("1", 150, "weld_neck"),
        ("1", 300, "blind"),
    ):
        add(
            "flange",
            "flange",
            dict(nps=nps, flange_class=flange_class, kind=kind),
            f"Brida {names[kind]} ASME B16.5, designación nominal NPS {nps}, clase "
            f"{flange_class}, cara elevada. Usa las dimensiones en mm y todos los detalles "
            "del catálogo bd_warehouse 0.2.0, sin sustituirla por un disco genérico. "
            "Eje en Z, centrada en X/Y, Z mínimo cero, sin rotación ni modificaciones.",
        )

    for outer_d, bore_d, height in (
        (20, 10, 10),
        (16, 6, 8),
        (24, 8, 15),
        (30, 12, 20),
        (40, 16, 25),
    ):
        add(
            "spacer",
            "spacer",
            dict(outer_d=outer_d, bore_d=bore_d, height=height),
            f"Separador cilíndrico de diámetro exterior {outer_d} mm, agujero pasante "
            f"coaxial de diámetro {bore_d} mm y altura {height} mm. Eje en Z, base en "
            "Z=0 mm, sin roscas, resaltes, redondeos ni chaflanes.",
        )

    for size, length in (
        ("M3-0.5", 10),
        ("M4-0.7", 12),
        ("M5-0.8", 16),
        ("M6-1", 20),
        ("M8-1.25", 25),
    ):
        diameter, pitch = size[1:].split("-")
        add(
            "tornillería",
            "screw",
            dict(size=size, length=length, simple=True, fastener_type="iso4762"),
            f"Tornillo de cabeza cilíndrica con hexágono interior ISO 4762, diámetro nominal "
            f"{diameter} mm, paso {pitch} mm y longitud bajo cabeza {length} mm. Usa el "
            "catálogo bd_warehouse 0.2.0 en representación simplificada sin hélice de rosca "
            "(simple=True), designación de rosca derecha, cabeza hacia +Z y vástago hacia "
            "-Z, cara bajo cabeza en Z=0 mm; sin cambios adicionales.",
        )

    for index, (request, reason) in enumerate(NEGATIVES, 1):
        cases.append(
            {
                "id": f"HU02-N{index:02d}",
                "familia": "fuera_alcance",
                "solicitud": request,
                "medidas": encode({"unidad": "mm", "no_aplica": True, "motivo_esperado": reason}),
                "resultado_esperado": "declinar",
            }
        )
    return cases


def check_environment():
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Se requiere el Python 3.12 fijado por el proyecto")
    revision = subprocess.run(
        ["git", "-C", str(ROOT / "vendor" / "constraint-kit"), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != ENGINE_REVISION:
        raise RuntimeError(f"Revisión inesperada del motor: {revision}")
    for package, expected in VERSIONS.items():
        if version(package) != expected:
            raise RuntimeError(f"Versión inesperada de {package}; se requiere {expected}")


def measure(case):
    measures = json_object(case["medidas"])
    engine_type, params = measures["tipo_motor"], measures["parametros"]
    module = (
        "constraint_kit.parts_bd" if engine_type in {"flange", "screw"} else "constraint_kit.parts"
    )
    wp, _ = getattr(importlib.import_module(module), engine_type)(**params)
    shape = wp.val()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("El generador no produjo un único sólido válido")
    box = shape.BoundingBox()
    return {
        "volumen_mm3": round(shape.Volume(), 9),
        "caja_xyz_mm": [round(v, 9) for v in (box.xlen, box.ylen, box.zlen)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Reemplazar explícitamente el CSV")
    mode.add_argument(
        "--check", action="store_true", help="Verificar sin escribir (predeterminado)"
    )
    args = parser.parse_args()
    check_environment()
    stored = None if args.write else read_dataset()
    if stored is not None:
        validate_dataset(stored)
    rows = specifications()
    analytic_count = 0
    for case in rows:
        if case.get("resultado_esperado") == "declinar":
            continue
        try:
            result = measure(case)
            case["resultado_esperado"] = encode(result)
            measures = json_object(case["medidas"])
            analytic_count += (
                analytical_reference(measures["tipo_motor"], measures["parametros"]) is not None
            )
        except Exception as exc:
            raise RuntimeError(f"Falló la medición de {case['id']}: {exc}") from exc
    validate_dataset(rows)  # Incluye los 15 contrastes analíticos, antes de escribir.
    if args.write:
        if not DEFAULT_PATH.parent.is_dir():
            raise RuntimeError("No existe el directorio data/ esperado")
        with DEFAULT_PATH.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    else:
        for actual, expected in zip(rows, stored, strict=True):
            for field in COLUMNS[:-1]:
                if actual[field] != expected[field]:
                    raise ValueError(f"{actual['id']}: difiere {field} de la especificación fuente")
            if actual["resultado_esperado"] == "declinar":
                if expected["resultado_esperado"] != "declinar":
                    raise ValueError(f"{actual['id']}: se esperaba declinar")
            else:
                compare_reference(
                    json_object(actual["resultado_esperado"]),
                    json_object(expected["resultado_esperado"]),
                )
    print(
        f"30/30 sólidos válidos; {analytic_count}/15 contrastes analíticos; 10 negativos completos."
    )
    print(
        "CSV regenerado explícitamente." if args.write else "Referencias reproducidas; CSV intacto."
    )


if __name__ == "__main__":
    main()
