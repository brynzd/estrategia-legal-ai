"""Orquestación del pipeline de extremo a extremo.

Encadena los pasos descritos en CLAUDE.md de forma secuencial y explícita
(funciones Python, sin framework de agentes pesado), registrando la entrada y la
salida de cada paso en un `Tracer` para el panel de trazabilidad:

    1. extracción          src.extraction.extract_text
    2-5. razonamiento      src.reasoning.analyze.run_analysis
         (encuadre, recuperación RAG por issue, régimen y los cuatro análisis)
    6. memorando           src.memo.builder.build_memo
    7. validación citas    src.memo.validator.validate_citations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .extraction import extract_text
from .memo.builder import build_memo
from .memo.validator import CitationReport, load_corpus_ids, validate_citations
from .reasoning.analyze import RetrieveFn, run_analysis
from .llm.client import LLMFn
from .trace import StepTrace, Tracer


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


def run_pipeline(
    pdf_path: str | Path | None = None,
    *,
    demanda_text: str | None = None,
    corpus_dir: Path | None = None,
    regimen_table_path: Path | None = None,
    rubrica_path: Path | None = None,
    retrieve_fn: RetrieveFn | None = None,
    llm_fn: LLMFn | None = None,
) -> MemoResult:
    """Ejecuta el pipeline completo sobre una demanda y valida sus citas.

    Args:
        pdf_path: Ruta al PDF de la demanda. Obligatorio salvo que se pase
            `demanda_text` directamente (útil para pruebas sin PDF).
        demanda_text: Texto ya extraído de la demanda. Si se provee, se omite la
            extracción (Paso 1) y se usa este texto.
        corpus_dir: Carpeta del corpus para validar las citas. Si es `None`, usa
            `config.CORPUS_DIR`.
        regimen_table_path: Ruta a `regimen_table.yaml`. Si es `None`, usa la de
            `config`.
        rubrica_path: Ruta a `rubrica_solidez.md`. Si es `None`, usa la de `config`.
        retrieve_fn: Función de recuperación inyectable (para pruebas). Si es
            `None`, usa el índice configurado.
        llm_fn: Función LLM inyectable (para pruebas). Si es `None`, usa el
            proveedor por defecto en todos los pasos.

    Returns:
        Un `MemoResult` con el memorando, el reporte de validación de citas y las
        trazas de cada paso.

    Raises:
        ValueError: Si no se proporciona ni `pdf_path` ni `demanda_text`.
    """
    corpus_dir = corpus_dir or config.CORPUS_DIR
    rubrica_path = rubrica_path or config.RUBRICA_SOLIDEZ_PATH
    tracer = Tracer()

    # Paso 1 — Extracción (se omite si ya viene el texto).
    if demanda_text is None:
        if pdf_path is None:
            raise ValueError("Debe proporcionar `pdf_path` o `demanda_text`.")
        demanda_text = extract_text(pdf_path)
        tracer.record("extraccion", entrada={"pdf_path": str(pdf_path)}, salida={"chars": len(demanda_text)})

    # Pasos 2–5 — Razonamiento (encuadre, recuperación por issue, régimen, análisis).
    analysis = run_analysis(
        demanda_text,
        regimen_table_path=regimen_table_path,
        retrieve_fn=retrieve_fn,
        llm_fn=llm_fn,
        tracer=tracer,
    )

    # Paso 6 — Ensamblado del memorando (ordenado por solidez).
    memo = build_memo(analysis, rubrica_path, llm_fn=llm_fn, tracer=tracer)

    # Paso 7 — Validación de citas contra el corpus (anti-alucinación).
    report = validate_citations(memo, load_corpus_ids(corpus_dir))
    tracer.record(
        "validacion_citas",
        entrada={"corpus_dir": str(corpus_dir)},
        salida={"cited": report.cited_ids, "orphans": report.orphan_ids, "is_valid": report.is_valid},
    )

    return MemoResult(memo=memo, citation_report=report, traces=tracer.steps)
