"""Paso 5 — Vinculación de terceros.

A partir del análisis, sugiere la vinculación de terceros cuando el caso lo
justifique: llamamiento en garantía (p. ej. aseguradora) o denuncia del pleito
(p. ej. fabricante). Cada sugerencia se apoya en su fundamento del corpus.
"""

from __future__ import annotations

from ..llm.client import LLMFn
from ._common import CITATION_CONTRACT, format_chunks, run_json_step

_SYSTEM = (
    "Eres un asistente jurídico (Colombia) que sugiere la VINCULACIÓN DE TERCEROS "
    "en responsabilidad civil extracontractual cuando el caso lo justifique: "
    "llamamiento en garantía (p. ej. aseguradora) o denuncia del pleito (p. ej. "
    "fabricante). Apoya cada sugerencia en su fundamento del corpus.\n\n"
    + CITATION_CONTRACT + "\n"
    "Claves del JSON: figuras (lista de objetos con figura, procede [bool], "
    "justificacion, fundamento [FUENTE: <id>]), citas (lista de [FUENTE: <id>])."
)


def analyze_third_parties(facts: dict, retrieved: list, llm_fn: LLMFn | None = None) -> dict:
    """Sugiere figuras de vinculación de terceros aplicables.

    Args:
        facts: Hechos estructurados (salida del Paso 2).
        retrieved: Fragmentos del corpus recuperados para este issue (con `id`).
        llm_fn: Función LLM a inyectar (para pruebas).

    Returns:
        Dict con `figuras` y `citas`.
    """
    user = f"HECHOS:\n{facts}\n\nFRAGMENTOS DEL CORPUS:\n{format_chunks(retrieved)}"
    return run_json_step(_SYSTEM, user, llm_fn)
