"""Test del pipeline de extremo a extremo (Fase 3 — orquestación 1-7).

Sin red, sin API y sin PDF: se inyecta el texto de la demanda, una `retrieve_fn`
simulada y un único LLM simulado que atiende tanto los pasos de razonamiento
(responde JSON) como la redacción del memorando (responde prosa citando lo
autorizado). Verifica que el pipeline produce un memorando válido y un reporte de
citas sin huérfanas.
"""

from __future__ import annotations

import re
from pathlib import Path

from src import config
from src.pipeline import run_pipeline
from src.rag.retriever import RetrievedChunk

FIXTURE = Path(__file__).parent / "fixtures" / "corpus_demo"

# Respuestas JSON por paso de razonamiento; cada una cita un id del corpus_demo.
_RUTAS_ANALISIS = [
    ("HECHOS estructurados",
     '{"tipo_hecho": "transito", "partes": {}, "hechos": [], '
     '"danos_reclamados": [], "pruebas_aportadas": []}'),
    ("RÉGIMEN",
     '{"regimen": "objetiva", "normas": ["demo_beta"], "matiz_doctrinal": "", '
     '"razonamiento": "r", "citas": ["[FUENTE: demo_beta]"]}'),
    ("NEXO CAUSAL",
     '{"elementos": [], "citas": ["[FUENTE: demo_beta]"]}'),
    ("CAUSALES DE EXONERACIÓN",
     '{"causales": [{"causal": "culpa víctima", "procede": true}], '
     '"citas": ["[FUENTE: demo_alpha]"]}'),
    ("PERJUICIO",
     '{"dano_emergente": {"soportado": false}, "lucro_cesante": {"soportado": true}, '
     '"citas": ["[FUENTE: demo_gamma]"]}'),
    ("VINCULACIÓN DE TERCEROS",
     '{"figuras": [], "citas": ["[FUENTE: demo_beta]"]}'),
]


class PipelineFakeLLM:
    """LLM simulado para todo el pipeline: razona (JSON) y redacta (prosa)."""

    def __call__(self, system: str, user: str) -> str:
        if "REDACTA" in system:  # paso 6: redacción de una sección -> prosa
            m = re.search(r"IDS QUE PUEDES CITAR EN ESTA SECCIÓN:\s*(.*)", user)
            ids = re.findall(r"'([^']+)'", m.group(1)) if m else []
            return "Prosa de la sección. " + " ".join(f"[FUENTE: {i}]" for i in ids)
        for substring, respuesta in _RUTAS_ANALISIS:  # pasos 2-5: razonamiento -> JSON
            if substring in system:
                return respuesta
        return "{}"


def _fake_retrieve(query: str) -> list[RetrievedChunk]:
    # Ignora la consulta y devuelve un fragmento trazable del corpus_demo.
    return [RetrievedChunk(id="demo_beta", texto="t", fuente="F", seccion="S",
                           url="https://example.com", score=0.9)]


def test_run_pipeline_end_to_end_sin_citas_huerfanas():
    res = run_pipeline(
        demanda_text="Demanda de responsabilidad civil por accidente de tránsito...",
        corpus_dir=FIXTURE,
        retrieve_fn=_fake_retrieve,
        llm_fn=PipelineFakeLLM(),
    )

    # Memorando bien formado.
    assert res.memo.startswith("# Memorando de estrategia defensiva")
    assert "Argumentos de defensa" in res.memo

    # Validación de citas: la red de seguridad anti-alucinación pasó.
    assert res.citation_report.is_valid
    assert res.citation_report.orphan_ids == []
    assert res.citation_report.cited_ids  # se citó algo

    # Trazabilidad: están los pasos clave de razonamiento, memorando y validación.
    nombres = {t.name for t in res.traces}
    assert {"encuadre_caso", "clasificacion_regimen", "memo:encuadre",
            "memo:orden_solidez", "validacion_citas"} <= nombres


def test_run_pipeline_exige_pdf_o_texto():
    import pytest
    with pytest.raises(ValueError):
        run_pipeline()  # ni pdf_path ni demanda_text
