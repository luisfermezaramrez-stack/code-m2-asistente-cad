"""Compara una corrida del banco contra el baseline versionado (HU-46, SPEC-047).

Uso habitual en CI (lee el último resumen del replay de HU-44):
    uv run --no-sync python -B scripts/verificar_alertas.py

Actualización explícita del baseline (nunca implícita al pasar una comparación):
    uv run --no-sync python -B scripts/verificar_alertas.py \
        --actualizar-baseline --autor "Nombre" --motivo "cambio revisado" \
        --corrida-origen "replay-20261127T..." --issue "#106"

Códigos: 0 sin regresión, 1 regresión, 2 artefacto inválido.
`--no-fail` mantiene el código 0 ante regresiones para que el workflow programado
publique el issue antes de propagar el fallo.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from m2_cad import alertas


def _argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compara el banco con su baseline (HU-46).")
    parser.add_argument(
        "--corrida-dir",
        type=Path,
        default=Path("outputs/banco-replay"),
        help="directorio con el último par JSON/CSV del banco",
    )
    parser.add_argument("--corrida", type=Path, help="resumen JSON explícito")
    parser.add_argument("--csv", type=Path, help="CSV por caso explícito")
    parser.add_argument(
        "--baseline", type=Path, default=alertas.BASELINE_PATH, help="baseline versionado"
    )
    parser.add_argument(
        "--salida", type=Path, default=alertas.SALIDA_DIR, help="donde escribir el resumen"
    )
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="no devolver 1 ante regresión (para el workflow de baseline real)",
    )
    parser.add_argument(
        "--actualizar-baseline",
        action="store_true",
        help="escribir un baseline nuevo con trazabilidad obligatoria",
    )
    parser.add_argument("--autor", default="", help="quien autoriza el cambio de baseline")
    parser.add_argument("--motivo", default="", help="por qué cambia el baseline")
    parser.add_argument("--corrida-origen", default="", help="corrida usada como referencia")
    parser.add_argument("--issue", default="", help="issue o PR que documenta el cambio")
    return parser.parse_args(argv)


def _localizar(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.corrida is not None:
        resumen = args.corrida
        casos = args.csv or resumen.with_suffix(".csv")
        return resumen, casos
    resumenes = sorted(args.corrida_dir.glob("*.json"))
    if not resumenes:
        raise alertas.ErrorAlertas(f"no hay resumen JSON en {args.corrida_dir}")
    resumen = resumenes[-1]
    return resumen, args.csv or resumen.with_suffix(".csv")


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    try:
        resumen, csv_casos = _localizar(args)
        corrida = alertas.leer_corrida(resumen, csv_casos)

        if args.actualizar_baseline:
            if args.baseline.exists():
                anterior = alertas.cargar_baseline(args.baseline)
            else:
                anterior = None  # Primera creación explícita del baseline.
            actualizado = alertas.construir_baseline(
                corrida,
                autor=args.autor,
                motivo=args.motivo,
                corrida_origen=args.corrida_origen or str(resumen),
                issue=args.issue,
                anterior=anterior,
            )
            args.baseline.parent.mkdir(parents=True, exist_ok=True)
            args.baseline.write_text(
                json.dumps(actualizado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            print(json.dumps({"baseline": str(args.baseline), "id": actualizado["id"]}, indent=2))
            return 0

        resultado = alertas.comparar(alertas.cargar_baseline(args.baseline), corrida)
        rutas = alertas.escribir(resultado, args.salida)
        print(json.dumps(resultado | {"archivos": rutas}, indent=2, ensure_ascii=False))
        if args.no_fail:
            return 0
        return int(resultado["codigo"])
    except alertas.ErrorAlertas as exc:
        print(f"Error de alertas: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
