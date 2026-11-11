"""Contrato del banco HU-02, sin dependencias CAD, de inferencia ni de terceros."""

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

COLUMNS = ("id", "familia", "solicitud", "medidas", "resultado_esperado")
FAMILIES = ("plate", "sheet_bracket", "adapter", "flange", "spacer", "tornillería")
PRODUCT_FAMILIES = (*FAMILIES, "extrusion", "pipe")
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "test_cases.csv"
PARAMETERS = {
    "plate": {"width", "depth", "thick", "boss_d", "boss_h", "bolt_d", "bolt_circle", "bolt_count"},
    "sheet_bracket": {"thickness", "base_length", "flange_length", "width", "bend_radius"},
    "adapter": {"bottom_w", "bottom_d", "top_d", "height"},
    "flange": {"nps", "flange_class", "kind"},
    "spacer": {"outer_d", "bore_d", "height"},
    "screw": {"size", "length", "simple", "fastener_type"},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_number(value, minimum=0, *, inclusive=False):
    """Los booleanos de JSON no son dimensiones ni volúmenes."""
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and (value >= minimum if inclusive else value > minimum)
    )


def _object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Clave JSON duplicada: {key}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"Constante JSON no finita: {value}")


def json_object(text):
    value = json.loads(text, object_pairs_hook=_object, parse_constant=_invalid_constant)
    require(type(value) is dict, "Se esperaba un objeto JSON")
    return value


def read_dataset(path=DEFAULT_PATH):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        require(tuple(reader.fieldnames or ()) == COLUMNS, "Cabecera CSV incorrecta")
        return list(reader)


def validate_parameters(engine_type, params):
    """Valida los parámetros de los casos acordados, no todo el catálogo del motor."""
    require(engine_type in PARAMETERS, "Tipo de motor no admitido en este banco")
    require(
        type(params) is dict and set(params) == PARAMETERS[engine_type], "Parámetros incompletos"
    )
    strings = {"nps", "kind", "size", "fastener_type"}
    for key, value in params.items():
        if key in strings:
            require(type(value) is str and bool(value.strip()), f"Tipo incorrecto: {key}")
        elif key == "simple":
            require(type(value) is bool, "simple debe ser booleano")
        else:
            require(finite_number(value, inclusive=True), f"Medida no finita o negativa: {key}")
            if key in {"bolt_count", "flange_class"}:
                require(type(value) is int, f"{key} debe ser entero")

    p = params
    if engine_type == "plate":
        require(all(p[k] > 0 for k in ("width", "depth", "thick")), "Placa degenerada")
        require(
            (p["boss_d"] == p["boss_h"] == 0) or (p["boss_d"] > 0 and p["boss_h"] > 0),
            "Resalte incompleto",
        )
        require(p["boss_d"] <= min(p["width"], p["depth"]), "Resalte fuera de la placa")
        holes = (p["bolt_count"], p["bolt_d"], p["bolt_circle"])
        require(all(x == 0 for x in holes) or all(x > 0 for x in holes), "Taladros incompletos")
        if p["bolt_count"]:
            require(p["bolt_count"] >= 2, "Patrón de taladros insuficiente")
            require(
                p["bolt_circle"] + p["bolt_d"] < min(p["width"], p["depth"]),
                "Taladros fuera de la placa",
            )
            require(p["bolt_circle"] > p["boss_d"] + p["bolt_d"], "Taladro invade el resalte")
            require(
                p["bolt_circle"] * math.sin(math.pi / p["bolt_count"]) > p["bolt_d"],
                "Taladros solapados",
            )
    elif engine_type == "sheet_bracket":
        require(all(p[k] > 0 for k in p if k != "bend_radius"), "Escuadra degenerada")
        require(p["bend_radius"] == 0, "Este banco usa escuadras sin radio")
        require(p["thickness"] < min(p["base_length"], p["flange_length"]), "Espesor incoherente")
    elif engine_type in {"adapter", "spacer"}:
        require(all(x > 0 for x in p.values()), "Geometría degenerada")
        if engine_type == "spacer":
            require(p["outer_d"] > p["bore_d"], "Diámetro interior incoherente")
    elif engine_type == "flange":
        require(p["nps"] in {"1", "2"}, "NPS fuera de los casos acordados")
        require(p["flange_class"] in {150, 300}, "Clase de brida no admitida")
        require(p["kind"] in {"blind", "slip_on", "weld_neck"}, "Tipo de brida incorrecto")
    elif engine_type == "screw":
        require(
            p["size"] in {"M3-0.5", "M4-0.7", "M5-0.8", "M6-1", "M8-1.25"},
            "Designación métrica no admitida",
        )
        require(p["length"] > 0, "Longitud de tornillo degenerada")
        require(
            p["simple"] is True and p["fastener_type"] == "iso4762",
            "El banco usa tornillos ISO 4762 sin hélice de rosca",
        )


def analytical_reference(engine_type, p):
    """Referencias por álgebra independiente, solo donde la forma tiene fórmula exacta."""
    if engine_type == "plate":
        volume = p["width"] * p["depth"] * p["thick"]
        volume += math.pi / 4 * p["boss_d"] ** 2 * p["boss_h"]
        volume -= p["bolt_count"] * math.pi / 4 * p["bolt_d"] ** 2 * p["thick"]
        return volume, (p["width"], p["depth"], p["thick"] + p["boss_h"])
    if engine_type == "sheet_bracket":
        volume = (
            p["width"] * p["thickness"] * (p["base_length"] + p["flange_length"] - p["thickness"])
        )
        return volume, (p["base_length"], p["width"], p["flange_length"])
    if engine_type == "spacer":
        volume = math.pi / 4 * (p["outer_d"] ** 2 - p["bore_d"] ** 2) * p["height"]
        return volume, (p["outer_d"], p["outer_d"], p["height"])
    return None


def compare_reference(actual, expected):
    """Tolerancia de reproducción numérica, distinta de la evaluación LLM (±2 %)."""
    require(
        math.isclose(actual["volumen_mm3"], expected["volumen_mm3"], rel_tol=1e-8, abs_tol=1e-6),
        "Volumen distinto de la referencia",
    )
    require(
        all(
            math.isclose(a, e, rel_tol=1e-8, abs_tol=2e-6)
            for a, e in zip(actual["caja_xyz_mm"], expected["caja_xyz_mm"], strict=True)
        ),
        "Caja distinta de la referencia",
    )


def validate_row(row):
    require(set(row) == set(COLUMNS), "Número de columnas incorrecto")
    require(
        all(type(v) is str and v.strip() and v == v.strip() for v in row.values()),
        "Campos obligatorios vacíos, ausentes o con espacios externos",
    )
    require(re.fullmatch(r"HU02-[PN]\d{2}", row["id"]) is not None, "ID mal formado")
    measures = json_object(row["medidas"])
    require(measures.get("unidad") == "mm", "Las medidas deben usar mm")
    if row["resultado_esperado"] == "declinar":
        require(
            row["familia"] == "fuera_alcance" and row["id"].startswith("HU02-N"),
            "Negativo clasificado dentro del alcance",
        )
        require(
            set(measures) == {"unidad", "no_aplica", "motivo_esperado"},
            "Un negativo no debe inventar dimensiones",
        )
        require(measures["no_aplica"] is True, "Las dimensiones del negativo no aplican")
        require(
            type(measures["motivo_esperado"]) is str and measures["motivo_esperado"].strip(),
            "Falta motivo de declinación",
        )
        return measures, None

    require(
        row["familia"] in FAMILIES and row["id"].startswith("HU02-P"), "Familia positiva inválida"
    )
    require(
        set(measures) == {"unidad", "tipo_motor", "parametros"}, "Esquema de medidas incorrecto"
    )
    engine_type = measures["tipo_motor"]
    require(type(engine_type) is str, "Tipo de motor incorrecto")
    require(
        engine_type == ("screw" if row["familia"] == "tornillería" else row["familia"]),
        "Tipo del motor no corresponde a la familia",
    )
    validate_parameters(engine_type, measures["parametros"])
    result = json_object(row["resultado_esperado"])
    require(set(result) == {"volumen_mm3", "caja_xyz_mm"}, "Esquema del resultado incorrecto")
    require(finite_number(result["volumen_mm3"]), "Volumen no positivo o no finito")
    box = result["caja_xyz_mm"]
    require(
        type(box) is list and len(box) == 3 and all(finite_number(v) for v in box),
        "Caja X/Y/Z inválida",
    )
    require(result["volumen_mm3"] <= math.prod(box) * (1 + 1e-6), "Volumen excede la caja")
    reference = analytical_reference(engine_type, measures["parametros"])
    if reference is not None:
        volume, xyz = reference
        compare_reference(result, {"volumen_mm3": volume, "caja_xyz_mm": xyz})
    if engine_type == "adapter":
        p = measures["parametros"]
        expected_box = (max(p["bottom_w"], p["top_d"]), max(p["bottom_d"], p["top_d"]), p["height"])
        require(
            all(
                math.isclose(a, e, rel_tol=1e-8, abs_tol=2e-6)
                for a, e in zip(box, expected_box, strict=True)
            ),
            "Caja del loft incoherente",
        )
    return measures, result


def validate_dataset(rows):
    require(len(rows) == 40, "El banco debe contener exactamente 40 filas")
    ids, requests, signatures = set(), set(), set()
    counts = Counter()
    negatives = 0
    for row in rows:
        try:
            measures, result = validate_row(row)
            require(row["id"] not in ids, "IDs duplicados")
            require(row["solicitud"] not in requests, "Solicitudes duplicadas")
            ids.add(row["id"])
            requests.add(row["solicitud"])
            if result is None:
                negatives += 1
                continue
            signature = (measures["tipo_motor"], tuple(sorted(measures["parametros"].items())))
            require(signature not in signatures, "Parámetros positivos duplicados")
            signatures.add(signature)
            counts[row["familia"]] += 1
        except ValueError as exc:
            raise ValueError(f"{row.get('id', '?')}: {exc}") from exc
    require(negatives == 10 and sum(counts.values()) == 30, "Reparto distinto de 30/10")
    require(counts == Counter({family: 5 for family in FAMILIES}), "Se requieren cinco por familia")
