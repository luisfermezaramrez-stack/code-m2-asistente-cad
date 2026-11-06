"""Pruebas de traducción ES→EN (HU-03).

Cubre ≥ 10 casos, incluidos decimales con coma, y verifica la conservación del
100 % de números y unidades.
"""

import pytest

from m2_cad.traduccion import (
    ErrorTraduccion,
    _proteger_valores,
    _restaurar_valores,
    traducir_solicitud,
)


def test_modulo_traduccion_importable():
    from m2_cad import traduccion

    assert traduccion is not None


def test_modulo_importable():
    """Verifica que el módulo exponga la función principal."""
    assert callable(traducir_solicitud)


def test_proteccion_de_medidas():
    """Comprueba la protección de números, unidades y decimales."""
    texto = "Placa de 120 mm con 4 agujeros de 12,5 mm"

    protegido, valores = _proteger_valores(texto)

    assert "12,5 mm" in valores.values()
    assert "12,5" not in protegido
    assert len(valores) == 3


def test_restauracion_de_medidas():
    """Comprueba que las medidas originales se recuperen."""
    texto = "Placa de 120 mm con 4 agujeros"

    protegido, valores = _proteger_valores(texto)
    restaurado = _restaurar_valores(protegido, texto, valores)

    assert restaurado == texto


def test_marcador_faltante():
    """Rechaza traducciones que pierden medidas."""
    texto = "Placa de 120 mm con 4 agujeros"

    _, valores = _proteger_valores(texto)

    with pytest.raises(ErrorTraduccion, match="marcadores"):
        _restaurar_valores("Plate of __CADVAL_0__", texto, valores)


def test_solicitud_vacia():
    """Impide procesar solicitudes sin contenido."""
    with pytest.raises(ValueError):
        traducir_solicitud("   ")


def test_traduccion_con_gemini_simulado(monkeypatch):
    """Verifica el flujo completo sin consultar la API real."""

    # Configura una clave ficticia para la prueba.
    monkeypatch.setenv("GEMINI_API_KEY", "clave-simulada")

    # Simula la respuesta de Gemini conservando los marcadores.
    def simular_gemini(texto_protegido, clave):
        assert clave == "clave-simulada"
        assert "12,5" not in texto_protegido

        return "Plate of __CADVAL_0__ × __CADVAL_1__ with __CADVAL_2__ holes of __CADVAL_3__"

    # Sustituye temporalmente la llamada real por la simulación.
    monkeypatch.setattr(
        "m2_cad.traduccion._consultar_gemini",
        simular_gemini,
    )

    texto = "Placa de 120 × 120 mm con 4 agujeros de 12,5 mm"

    resultado = traducir_solicitud(texto)

    # Comprueba la traducción y la conservación de las medidas.
    assert resultado == ("Plate of 120 × 120 mm with 4 holes of 12,5 mm")


@pytest.mark.parametrize(
    ("texto", "esperados"),
    [
        ("Placa de 120 x 120 mm", ["120", "120 mm"]),
        ("Brida de 12,5 mm", ["12,5 mm"]),
        ("Soporte de 1.25 cm", ["1.25 cm"]),
        ("Placa con 4 agujeros de 8mm", ["4", "8mm"]),
        ("Separador de 2 m y 3 kg", ["2 m", "3 kg"]),
    ],
)
def test_medidas_parametrizadas(texto, esperados):
    """Valida distintos formatos y la restauración de medidas."""
    protegido, valores = _proteger_valores(texto)

    assert list(valores.values()) == esperados
    assert _restaurar_valores(protegido, texto, valores) == texto
