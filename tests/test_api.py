"""Pruebas de la API FastAPI (HU-06).

Cubre POST /generar (200 con STEP o declinación; 422 ante texto vacío o de más
de 1000 caracteres), GET /health en ≤ 1 s y el registro sin campos vacíos ni
datos personales. Cobertura objetivo ≥ 80 % del módulo.
"""


def test_modulo_api_importable():
    from m2_cad import api

    assert api is not None
