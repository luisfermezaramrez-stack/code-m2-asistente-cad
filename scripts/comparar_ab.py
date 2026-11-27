#!/usr/bin/env python3
"""Compara dos variantes de prompt/modelo sobre el mismo banco (HU-52, SPEC-053).

Uso (real, gasta tokens):
    python scripts/comparar_ab.py --modelo-b deepseek-v3 --salida outputs/ab

Uso en replay (sin red, API key ni tokens; cada variante con sus respuestas):
    python scripts/comparar_ab.py \
        --replay-a data/banco_replay.json --replay-b data/banco_replay-v2.json

La comparación registra dos corridas en MLflow y escribe JSON y Markdown en
`--salida`. No promueve variantes: la decisión sigue siendo explícita.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from m2_cad import ab, dataset, pipeline, prompts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Comparación A/B de prompts y modelos (HU-52).")
    parser.add_argument(
        "--id", default="", help="identificador de la comparación (por defecto, marca de tiempo)"
    )
    parser.add_argument("--banco", type=Path, default=dataset.DEFAULT_PATH)
    parser.add_argument(
        "--ids", default="", help="IDs del banco separados por comas; vacío = todos"
    )
    parser.add_argument("--prompt-a", default="planner-v1")
    parser.add_argument("--prompt-b", default="planner-v2")
    parser.add_argument(
        "--modelo-a", default="", help="modelo de A; en replay se toma del artefacto si se omite"
    )
    parser.add_argument(
        "--modelo-b", default="", help="modelo de B; en replay se toma del artefacto si se omite"
    )
    parser.add_argument("--raiz-prompts", type=Path, default=None)
    parser.add_argument("--replay-a", type=Path, default=None, help="respuestas grabadas de A")
    parser.add_argument("--replay-b", type=Path, default=None, help="respuestas grabadas de B")
    parser.add_argument("--salida", type=Path, default=ab.SALIDA_DIR)
    parser.add_argument(
        "--precio-entrada", type=float, default=0.0, help="USD por 1M tokens de entrada"
    )
    parser.add_argument(
        "--precio-salida", type=float, default=0.0, help="USD por 1M tokens de salida"
    )
    return parser


def _modelo_del_artefacto(ruta: Path) -> str:
    """Lee sólo el modelo declarado; la validación completa la hace `preparar`."""
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ab.ErrorAB(f"No se pudo leer {ruta}: {exc}") from exc
    modelo = str(datos.get("modelo") or "").strip()
    if not modelo:
        raise ab.ErrorAB(f"{ruta} no declara el modelo con el que se grabó.")
    return modelo


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    id_comparacion = args.id.strip() or f"ab-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    filas = dataset.read_dataset(args.banco)
    if args.ids.strip():
        pedidos = {valor.strip() for valor in args.ids.split(",") if valor.strip()}
        filas = [fila for fila in filas if fila["id"] in pedidos]
        if not filas:
            print("Error A/B: ningún ID del banco coincide con --ids.", file=sys.stderr)
            return 2

    try:
        modelo_a = args.modelo_a.strip() or (
            _modelo_del_artefacto(args.replay_a) if args.replay_a else pipeline.llm.planner_model()
        )
        modelo_b = args.modelo_b.strip() or (
            _modelo_del_artefacto(args.replay_b) if args.replay_b else pipeline.llm.planner_model()
        )
        variante_a = ab.construir_variante(
            "A", args.prompt_a, modelo_a, raiz=args.raiz_prompts, replay=args.replay_a
        )
        variante_b = ab.construir_variante(
            "B", args.prompt_b, modelo_b, raiz=args.raiz_prompts, replay=args.replay_b
        )
        contexto = ab.validar_variantes(variante_a, variante_b, filas)
        resultados = [
            ab.ejecutar_variante(
                variante,
                filas,
                id_comparacion=id_comparacion,
                salida=args.salida,
                precio_entrada=args.precio_entrada,
                precio_salida=args.precio_salida,
            )
            for variante in (variante_a, variante_b)
        ]
        comparacion = ab.comparar(resultados, id_comparacion=id_comparacion, contexto=contexto)
        rutas = ab.escribir(comparacion, args.salida)
    except (ab.ErrorAB, prompts.ErrorPrompt, OSError) as exc:
        print(f"Error A/B: {exc}", file=sys.stderr)
        return 2

    print(f"Comparación {id_comparacion}: {len(filas)} casos, modo {contexto['modo']}.")
    for resultado in resultados:
        total = comparacion["totales"][resultado["variante"]]
        print(
            f"  {resultado['variante']}: {resultado['prompt']['etiqueta']} @ "
            f"{resultado['modelo']} · acierto={total['acierto']:.3f} · "
            f"declinaciones={total['declinaciones_correctas']}"
        )
    print(f"  cambios: {len(comparacion['casos_cambiados'])} · reporte: {rutas['markdown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
