"""Smoke test de la UI (Fase 4) con el runner headless de Streamlit.

No sube PDF ni ejecuta el pipeline (eso necesitaría API e índice y ya está
cubierto en test_pipeline.py). Solo verifica que el script de la app se ejecuta
de principio a fin sin excepciones: imports, barra lateral de estado, helpers de
render y cabecera. Así un cambio que rompa el arranque de la UI se detecta en CI.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "app.py")


def test_app_arranca_sin_excepciones():
    at = AppTest.from_file(APP).run()
    assert not at.exception


def test_app_muestra_titulo_y_estado_inicial():
    at = AppTest.from_file(APP).run()
    # Título de la app.
    assert any("EstrategIA Legal" in t.value for t in at.title)
    # Sin resultados todavía: el estado del pipeline arranca vacío.
    assert at.session_state["result"] is None
