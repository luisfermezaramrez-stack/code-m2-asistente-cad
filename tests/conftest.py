"""Fixtures compartidas para aislar los efectos de HU-25 y HU-53 en CI."""

import pytest


@pytest.fixture(autouse=True)
def _desactivar_auth_en_pruebas_heredadas(monkeypatch):
    """HU-53 activa la autenticación sólo en su fixture; el resto queda en modo local."""
    monkeypatch.setenv("M2_AUTH_ENABLED", "0")
    monkeypatch.setenv("M2_AUTH_COOKIE_SECURE", "0")


@pytest.fixture(autouse=True)
def _desactivar_cola_en_pruebas_heredadas(monkeypatch):
    """Las pruebas SSE previas ejecutan en proceso; HU-45 la activa en su fixture."""
    monkeypatch.setenv("M2_COLA_HABILITADA", "0")


@pytest.fixture(autouse=True)
def aislar_cache_hu25_entre_pruebas():
    """Cada test empieza sin respuestas de escenarios previos.

    No desactiva el cache dentro de cada test: AC2 sigue verificando el hit.
    """
    from m2_cad import llm_resiliente

    with llm_resiliente._CERROJO:
        llm_resiliente._CACHE.clear()
    llm_resiliente.reiniciar_metricas()
    try:
        yield
    finally:
        with llm_resiliente._CERROJO:
            llm_resiliente._CACHE.clear()
        llm_resiliente.reiniciar_metricas()
