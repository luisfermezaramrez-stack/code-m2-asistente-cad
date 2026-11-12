"""Comprueba cinco generadores de HU-02 sin inferencia ni escritura de artefactos."""

import argparse
import importlib
import json
import math

CASES = {
    "sheet_bracket": (
        "constraint_kit.parts",
        "sheet_bracket",
        {"thickness": 2, "base_length": 40, "flange_length": 25, "width": 30, "bend_radius": 0},
    ),
    "adapter": (
        "constraint_kit.parts",
        "adapter",
        {"bottom_w": 40, "bottom_d": 40, "top_d": 24, "height": 30},
    ),
    "flange": (
        "constraint_kit.parts_bd",
        "flange",
        {"nps": "1", "flange_class": 150, "kind": "blind"},
    ),
    "spacer": (
        "constraint_kit.parts",
        "spacer",
        {"outer_d": 20, "bore_d": 10, "height": 10},
    ),
    "tornilleria": (
        "constraint_kit.parts_bd",
        "screw",
        {"size": "M5-0.8", "length": 16, "simple": True, "fastener_type": "iso4762"},
    ),
}


def measure(family):
    module, part_type, params = CASES[family]
    wp, _ = getattr(importlib.import_module(module), part_type)(**params)
    shape = wp.val()
    box = shape.BoundingBox()
    volume = shape.Volume()
    xyz = (box.xlen, box.ylen, box.zlen)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Se esperaba un unico solido B-rep valido")
    if not all(math.isfinite(value) and value > 0 for value in (volume, *xyz)):
        raise ValueError("Volumen o caja no positivos/finitos")

    # Contrastes independientes: union de prismas y cilindro anular, respectivamente.
    analytical = {
        "sheet_bracket": (30 * 2 * (40 + 25 - 2), (40, 30, 25)),
        "spacer": (math.pi / 4 * (20**2 - 10**2) * 10, (20, 20, 10)),
    }
    if family in analytical:
        expected_volume, expected_xyz = analytical[family]
        if not math.isclose(volume, expected_volume, rel_tol=1e-10) or not all(
            math.isclose(actual, expected, abs_tol=1e-8)
            for actual, expected in zip(xyz, expected_xyz, strict=True)
        ):
            raise ValueError("La medicion no coincide con el calculo analitico")
    return {
        "family": family,
        "engine_type": part_type,
        "params": params,
        "valid": True,
        "n_solids": len(shape.Solids()),
        "volume_mm3": volume,
        "bbox_xyz_mm": xyz,
        "analytical_check": "PASS" if family in analytical else "not_performed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", nargs="?", choices=["all", *CASES], default="all")
    args = parser.parse_args()
    failed = False
    for family in CASES if args.family == "all" else [args.family]:
        try:
            result = measure(family)
        except Exception as exc:
            result = {"family": family, "error": f"{type(exc).__name__}: {exc}"}
            failed = True
        print(json.dumps(result, ensure_ascii=True))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
