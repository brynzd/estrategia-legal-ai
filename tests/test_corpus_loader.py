"""Tests del cargador de corpus (Fase 1).

Verifica el parseo de markdown con front-matter y JSON, la regla de ignorar
plantillas (`_*`) y la omisión de documentos sin `id`. No requiere modelos ni red.
"""

from __future__ import annotations

from pathlib import Path

from src.rag.corpus_loader import load_corpus

FIXTURE = Path(__file__).parent / "fixtures" / "corpus_demo"


def test_carga_md_y_json_con_ids():
    docs = load_corpus(FIXTURE)
    ids = {d.id for d in docs}
    assert ids == {"demo_alpha", "demo_beta", "demo_gamma"}


def test_ignora_plantillas_con_guion_bajo():
    docs = load_corpus(FIXTURE)
    assert "NO_DEBE_CARGARSE" not in {d.id for d in docs}


def test_campos_md_frontmatter():
    doc = next(d for d in load_corpus(FIXTURE) if d.id == "demo_beta")
    assert doc.fuente.startswith("Documento de prueba Beta")
    assert doc.url == "https://example.com/beta"
    assert "automóviles" in doc.texto


def test_campos_json():
    doc = next(d for d in load_corpus(FIXTURE) if d.id == "demo_gamma")
    assert doc.seccion == "Tema música"
    assert "conciertos" in doc.texto


def test_corpus_inexistente_devuelve_vacio(tmp_path):
    assert load_corpus(tmp_path / "no_existe") == []
