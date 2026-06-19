"""Tests del ensamblado del memorando (Fase 3 — Paso 6, híbrido).

Sin red ni API: un LLM simulado que redacta cada sección "haciendo eco" de los ids
que se le autorizan a citar. Validan:
- el orden por solidez (más sólido primero) que decide el código,
- la presencia del disclaimer y la estructura,
- y que el memorando resultante no tiene citas huérfanas (Restricción dura #2).
"""

from __future__ import annotations

import re
from pathlib import Path

from src import config
from src.memo.builder import build_memo, score_solidez
from src.memo.validator import load_corpus_ids, validate_citations
from src.rag.retriever import RetrievedChunk
from src.reasoning.analyze import AnalysisResult

FIXTURE = Path(__file__).parent / "fixtures" / "corpus_demo"


class EchoCitasLLM:
    """LLM simulado de redacción: cita los ids que el prompt autoriza para la sección."""

    def __call__(self, system: str, user: str) -> str:
        m = re.search(r"IDS QUE PUEDES CITAR EN ESTA SECCIÓN:\s*(.*)", user)
        ids = re.findall(r"'([^']+)'", m.group(1)) if m else []
        citas = " ".join(f"[FUENTE: {i}]" for i in ids)
        return f"Prosa de prueba de la sección. {citas}".strip()


def _chunk(cid: str) -> RetrievedChunk:
    return RetrievedChunk(id=cid, texto=f"texto {cid}", fuente="F", seccion="S",
                          url="https://example.com", score=0.9)


def _analysis_result() -> AnalysisResult:
    """AnalysisResult de prueba con solidez deliberadamente distinta por issue."""
    return AnalysisResult(
        facts={"tipo_hecho": "transito", "hechos": ["la víctima cruzó en rojo"]},
        regime={"regimen": "objetiva", "citas": ["[FUENTE: demo_beta]"]},
        causation={"elementos": [], "citas": ["[FUENTE: demo_beta]"]},  # MEDIA (1)
        exoneration={"causales": [{"causal": "culpa víctima", "procede": True}],
                     "citas": ["[FUENTE: demo_alpha]"]},                # ALTA (2)
        damages={"dano_emergente": {"soportado": False},
                 "lucro_cesante": {"soportado": True},
                 "citas": ["[FUENTE: demo_gamma]"]},                    # ALTA (2)
        third_parties={"figuras": [], "citas": []},                    # BAJA (0)
        retrieved={
            "regimen": [_chunk("demo_beta")],
            "nexo_causal": [_chunk("demo_beta")],
            "exoneracion": [_chunk("demo_alpha")],
            "perjuicio": [_chunk("demo_gamma")],
            "terceros": [],
        },
    )


# --- score_solidez (unitario) -----------------------------------------------

def test_score_solidez_sin_citas_es_baja():
    assert score_solidez("terceros", {"citas": []}) == ("BAJA", 0)


def test_score_solidez_una_cita_es_media():
    assert score_solidez("nexo_causal", {"citas": ["[FUENTE: x]"]}) == ("MEDIA", 1)


def test_score_solidez_efecto_procesal_sube_a_alta():
    exo = {"citas": ["[FUENTE: x]"], "causales": [{"procede": True}]}
    assert score_solidez("exoneracion", exo) == ("ALTA", 2)
    perj = {"citas": ["[FUENTE: x]"], "dano_emergente": {"soportado": False}}
    assert score_solidez("perjuicio", perj) == ("ALTA", 2)


def test_score_solidez_penaliza_no_encontrado():
    nivel, puntaje = score_solidez("nexo_causal", {"citas": [], "r": config.NOT_FOUND_SENTINEL})
    assert (nivel, puntaje) == ("BAJA", -1)


# --- build_memo (integración con LLM simulado) ------------------------------

def test_build_memo_tiene_estructura_y_disclaimer():
    memo = build_memo(_analysis_result(), config.RUBRICA_SOLIDEZ_PATH, llm_fn=EchoCitasLLM())
    assert memo.startswith("# Memorando de estrategia defensiva")
    assert "Documento de apoyo" in memo or "apoyo a la decisión" in memo
    assert "## Encuadre del caso y régimen aplicable" in memo
    assert "## Argumentos de defensa (ordenados por solidez)" in memo


def test_build_memo_ordena_por_solidez():
    memo = build_memo(_analysis_result(), config.RUBRICA_SOLIDEZ_PATH, llm_fn=EchoCitasLLM())

    # Exoneración y perjuicio (ALTA) van antes que nexo causal (MEDIA) y terceros (BAJA).
    i_exo = memo.index("Causales de exoneración")
    i_per = memo.index("Perjuicio")
    i_nexo = memo.index("Nexo causal")
    i_ter = memo.index("Vinculación de terceros")
    assert i_exo < i_nexo < i_ter
    assert i_per < i_nexo

    assert "### 1. Causales de exoneración — solidez ALTA" in memo
    assert "Vinculación de terceros — solidez BAJA" in memo


def test_build_memo_sin_citas_huerfanas():
    """DoD Fase 3: memorando con cero citas huérfanas (Restricción dura #2)."""
    memo = build_memo(_analysis_result(), config.RUBRICA_SOLIDEZ_PATH, llm_fn=EchoCitasLLM())
    reporte = validate_citations(memo, load_corpus_ids(FIXTURE))
    assert reporte.cited_ids
    assert reporte.is_valid
    assert reporte.orphan_ids == []
