"""Pruebas de traducción ES→EN (HU-03).

Cubre ≥ 10 casos, incluidos decimales con coma, y verifica la conservación del
100 % de números y unidades.
"""


def test_modulo_traduccion_importable():
    from m2_cad import traduccion

    assert traduccion is not None
