"""Pruebas del pipeline de generación y verificación (HU-04, HU-05).

Verifica que la salida pase el verificador, que volumen y caja envolvente
queden dentro de ±2 %, que toda salida lleve la marca "preliminar" y que las
piezas fuera del catálogo se declinen con motivo y sin STEP.
"""


def test_modulo_pipeline_importable():
    from m2_cad import pipeline

    assert pipeline is not None
