#!/usr/bin/env python3
"""HU-01 AC4 — Prueba end-to-end: N solicitudes al modelo servido (llama.cpp vía
túnel) y validación de cada programa generado contra /dsl/check del servicio
cadkit. Pasa si las N devuelven un programa que supera el chequeo (ok=true, sin
severidad "error") y no son declinaciones honestas ("unsupported").

Uso (desde la raíz del repo, con el túnel SSH abierto y cadkit arriba):
  python3 scripts/cloud/dsl_check_smoke.py

Variables:
  LLM_BASE_URL   base del modelo servido (default: http://127.0.0.1:8080)
  CADKIT_URL     base del servicio cadkit   (default: http://127.0.0.1:8195)
  MODEL_PLANNER  nombre del modelo para el payload (default: gemma4-12b-...)
  N_REQUESTS     cantidad de solicitudes    (default: 5; AC4 exige 5/5)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join("vendor", "constraint-kit"))
from drivers.dsl_experiment import CASES, FEWSHOT, SYSTEM  # noqa: E402

LLM_BASE = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8080")
CADKIT_BASE = os.environ.get("CADKIT_URL", "http://127.0.0.1:8195")
MODEL = os.environ.get("MODEL_PLANNER", "gemma4-12b-constraintkit-grpo-Q6_K")
N_REQUESTS = int(os.environ.get("N_REQUESTS", "5"))


def post_json(url: str, payload: dict, timeout: int = 180) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def extract_program(text: str) -> dict:
    """Extrae el JSON del programa de la respuesta del modelo (tolera fences)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[len("json"):]
    return json.loads(text.strip())


def main() -> int:
    # Casos expresibles del vocabulario (los 5 primeros del driver del autor).
    cases = [c for c in CASES if c[0] == "single"][:N_REQUESTS]
    if len(cases) < N_REQUESTS:
        print(f"FALLA: solo hay {len(cases)} casos de ejemplo, se pidieron {N_REQUESTS}")
        return 1

    passed = 0
    for i, (_, description, _expected) in enumerate(cases, 1):
        print(f"[{i}/{N_REQUESTS}] {description}")
        try:
            completion = post_json(
                f"{LLM_BASE}/v1/chat/completions",
                {
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM},
                        *FEWSHOT,
                        {"role": "user", "content": description},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1024,
                },
            )
            program = extract_program(completion["choices"][0]["message"]["content"])
        except Exception as exc:  # noqa: BLE001 — reportar y seguir
            print(f"  FALLA: error generando/parsing el programa: {type(exc).__name__}: {exc}")
            continue

        try:
            result = post_json(f"{CADKIT_BASE}/dsl/check", {"program": program})
        except Exception as exc:  # noqa: BLE001
            print(f"  FALLA: /dsl/check no respondió: {type(exc).__name__}: {exc}")
            continue

        if result.get("ok") and not result.get("declined"):
            passed += 1
            print(f"  PASS: ok=true, n_errors={result.get('n_errors')}")
        elif result.get("declined"):
            print(f"  FALLA: declinación honesta ({result.get('reason')}) — no es un programa")
        else:
            errors = [d for d in result.get("diagnostics", []) if d.get("severity") == "error"]
            print(f"  FALLA: n_errors={result.get('n_errors')} -> {errors[:3]}")

    print(f"\nAC4: {passed}/{N_REQUESTS} programas pasan /dsl/check")
    return 0 if passed == N_REQUESTS else 1


if __name__ == "__main__":
    sys.exit(main())
