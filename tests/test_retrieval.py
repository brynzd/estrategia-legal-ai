"""Tests de ingesta + recuperación (Fase 1).

Validan la mecánica completa (fragmentar -> embeber -> persistir -> buscar ->
trazar el id) con un embedder SIMULADO y determinista, sin descargar modelos ni
usar red. El embedder real (sentence-transformers) se prueba aparte, manualmente,
cuando hay corpus y modelo disponibles.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src.rag.ingest import build_index, chunk_text
from src.rag.retriever import retrieve

FIXTURE = Path(__file__).parent / "fixtures" / "corpus_demo"

# Vocabulario controlado para un embedder simulado: cada texto -> vector de
# presencia de estos términos, L2-normalizado. Textos del mismo tema comparten
# términos y, por tanto, quedan cerca en coseno.
_VOCAB = ["fruta", "cocina", "auto", "carretera", "musica", "concierto"]


def mock_embed(texts: list[str]) -> np.ndarray:
    filas = []
    for t in texts:
        tl = t.lower()
        v = np.array([1.0 if term in tl else 0.0 for term in _VOCAB], dtype=np.float32)
        norm = np.linalg.norm(v)
        filas.append(v / norm if norm > 0 else v)
    return np.vstack(filas)


def test_chunk_text_corto_devuelve_un_fragmento():
    assert chunk_text("texto corto") == ["texto corto"]


def test_chunk_text_largo_fragmenta_con_solape():
    fragmentos = chunk_text("x" * 1500, max_chars=600, overlap=80)
    assert len(fragmentos) >= 3
    assert all(len(f) <= 600 for f in fragmentos)


def test_build_index_indexa_los_documentos(tmp_path):
    n = build_index(FIXTURE, tmp_path / "idx", embed_fn=mock_embed)
    assert n == 3  # alpha, beta, gamma (textos cortos -> 1 fragmento c/u)
    assert (tmp_path / "idx" / "embeddings.npy").exists()
    assert (tmp_path / "idx" / "chunks.json").exists()


def test_retrieve_devuelve_la_fuente_correcta_y_trazable(tmp_path):
    build_index(FIXTURE, tmp_path / "idx", embed_fn=mock_embed)

    # Consulta sobre transporte -> debe recuperar demo_beta (auto/carretera).
    res = retrieve("autos en la carretera", tmp_path / "idx", embed_fn=mock_embed, top_k=1)
    assert len(res) == 1
    assert res[0].id == "demo_beta"            # trazabilidad: id de la fuente
    assert res[0].url == "https://example.com/beta"
    assert res[0].score > 0

    # Consulta sobre cocina -> debe recuperar demo_alpha (fruta/cocina).
    res2 = retrieve("postres de fruta en la cocina", tmp_path / "idx", embed_fn=mock_embed, top_k=1)
    assert res2[0].id == "demo_alpha"


def test_retrieve_respeta_top_k(tmp_path):
    build_index(FIXTURE, tmp_path / "idx", embed_fn=mock_embed)
    res = retrieve("musica y conciertos en el escenario", tmp_path / "idx", embed_fn=mock_embed, top_k=2)
    assert len(res) == 2
    assert res[0].id == "demo_gamma"           # el más relevante primero
