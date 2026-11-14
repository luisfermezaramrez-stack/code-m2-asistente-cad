"""Smoke REAL de HU02-P01: un único POST con costo, sin reintentos de generación.

No ejecutarlo para validar la instalación: requiere API y MLflow ya preparados.
Las pruebas de este script usan exclusivamente transportes simulados.
"""

import argparse
import hashlib
import json
import uuid
from pathlib import Path

import httpx

from m2_cad.dataset import read_dataset, validate_dataset
from m2_cad.evaluacion import CONFORME, evaluar_caso


def ejecutar_smoke(cliente, tracking, *, salida: Path, mlflow_ui: str) -> tuple[dict, Path]:
    """Conserva evidencias incluso ante fallos; nunca crea una segunda corrida MLflow."""
    casos = read_dataset()
    validate_dataset(casos)
    caso = next(c for c in casos if c["id"] == "HU02-P01")
    assert caso["resultado_esperado"] != "declinar"
    # Solo lecturas previas: si faltan servicios/contrato, no se envía al modelo.
    cliente.get("/health").raise_for_status()
    esquema = cliente.get("/openapi.json")
    esquema.raise_for_status()
    rutas = esquema.json()["paths"]
    if (
        not {"/generar", "/registros/{identificador}", "/registros/{identificador}/step"}
        <= rutas.keys()
    ):
        raise RuntimeError("La API no contiene la trazabilidad HU-07 actual.")
    tracking.get_experiment_by_name("m2-cad-generacion")
    carpeta = salida / uuid.uuid4().hex
    carpeta.mkdir(parents=True, exist_ok=False)
    resultado = evaluar_caso(cliente, caso)  # ÚNICO POST /generar; solo texto en español.
    resultado["caso_unico"] = True
    resultado["step_conservado"] = False
    resultado["mlflow_confirmado"] = False

    def guardar():
        (carpeta / "resultado.json").write_text(
            json.dumps(resultado, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )

    guardar()
    try:
        if resultado["registro_confirmado"]:
            (carpeta / "registro.json").write_text(
                json.dumps(resultado["registro"], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        if resultado.get("medido"):
            step = cliente.get(resultado["step"])
            step.raise_for_status()
            if not step.content:
                raise RuntimeError("STEP vacío")
            (carpeta / "pieza.step").write_bytes(step.content)
            resultado.update(
                step_conservado=True,
                step_sha256=hashlib.sha256(step.content).hexdigest(),
            )
    except Exception as exc:
        resultado["error_descarga"] = type(exc).__name__
    try:
        experimento = tracking.get_experiment_by_name("m2-cad-generacion")
        corridas = (
            []
            if experimento is None
            else tracking.search_runs(
                [experimento.experiment_id],
                filter_string=f"tags.solicitud_id = '{resultado['request_id']}'",
            )
        )
        if len(corridas) == 1:
            corrida = corridas[0]
            resultado["mlflow"] = {
                "run_id": corrida.info.run_id,
                "estado": corrida.info.status,
                "url": f"{mlflow_ui.rstrip('/')}/#/experiments/{experimento.experiment_id}"
                f"/runs/{corrida.info.run_id}",
                "metricas": dict(corrida.data.metrics),
            }
            resultado["mlflow_confirmado"] = corrida.info.status == "FINISHED"
        else:
            resultado["corridas_mlflow_encontradas"] = len(corridas)
    except Exception as exc:
        resultado["error_mlflow"] = type(exc).__name__
    guardar()
    return resultado, carpeta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--tracking-uri", default="http://127.0.0.1:5000")
    parser.add_argument("--mlflow-ui", default="http://127.0.0.1:5000")
    parser.add_argument("--salida", type=Path, default=Path("docs/hu07/smoke"))
    args = parser.parse_args()
    from mlflow.tracking import MlflowClient

    with httpx.Client(base_url=args.api_url, timeout=180) as cliente:
        resultado, carpeta = ejecutar_smoke(
            cliente,
            MlflowClient(tracking_uri=args.tracking_uri),
            salida=args.salida,
            mlflow_ui=args.mlflow_ui,
        )
    print(f"Evidencia: {carpeta / 'resultado.json'}")
    return (
        0
        if (
            resultado["categoria"] == CONFORME
            and resultado["registro_confirmado"]
            and resultado.get("correlacion_respuesta")
            and resultado["step_conservado"]
            and resultado["mlflow_confirmado"]
        )
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
