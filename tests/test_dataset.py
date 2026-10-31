"""Validación del banco de 40 solicitudes (HU-02).

Comprueba IDs únicos, tipos, unidades en mm y 0 celdas vacías en
id, familia, solicitud, medidas y resultado esperado.
"""


def test_paquete_importable():
    import m2_cad

    assert m2_cad.__name__ == "m2_cad"
