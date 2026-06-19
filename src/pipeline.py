"""Orquestación del pipeline de extremo a extremo.

Encadena los pasos descritos en CLAUDE.md de forma secuencial y explícita
(funciones Python, sin framework de agentes pesado), registrando la entrada y la
salida de cada paso en un `Tracer` para el panel de trazabilidad:

    1. extracción          src.extraction.extract_text
    2. encuadre del caso   src.reasoning.case_framing.frame_case
    3. clasificación       src.reasoning.regime.classify_regime
    4. recuperación RAG    src.rag.retriever.retrieve
    5. razonamiento        causation / exoneration / damages / third_parties
    6. memorando           src.memo.builder.build_memo
    7. validación citas    src.memo.validator.validate_citations

Pendiente de implementar — ver Fase 3 del PLAN.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.memo.validator import CitationReport
from src.trace import StepTrace


@dataclass
class MemoResult:
    """Resultado completo de una ejecución del pipeline.

    Attributes:
        memo: Texto del memorando de estrategia defensiva (markdown).
        citation_report: Resultado de la validación de citas (Restricción #2).
        traces: Lista de pasos registrados para el panel de trazabilidad.
    """

    memo: str
    citation_report: CitationReport
    traces: list[StepTrace] = field(default_factory=list)


def run_pipeline(pdf_path: str | Path) -> MemoResult:
    """Ejecuta el pipeline completo sobre el PDF de una demanda.

    Args:
        pdf_path: Ruta al PDF de la demanda a analizar.

    Returns:
        Un `MemoResult` con el memorando, el reporte de validación de citas y las
        trazas de cada paso.
    """
    raise NotImplementedError("Fase 3 del PLAN.md — orquestación del pipeline.")
