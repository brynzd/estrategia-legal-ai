"""Paso 5 — Causales de exoneración.

Evalúa las causales de exoneración sobre los hechos: culpa exclusiva de la
víctima, hecho de un tercero y fuerza mayor, incluyendo la concurrencia de culpas
cuando aplique. Cada causal se sustenta en su fundamento normativo recuperado del
corpus.
"""

from __future__ import annotations

from ..llm.client import LLMFn
from ._common import CITATION_CONTRACT, format_chunks, run_json_step

_SYSTEM = (
    "Eres un asistente jurídico (Colombia) que evalúa las CAUSALES DE EXONERACIÓN "
    "para la defensa en responsabilidad civil extracontractual: culpa exclusiva de "
    "la víctima, hecho de un tercero y fuerza mayor; e incluye la concurrencia de "
    "culpas cuando aplique. Sustenta cada causal en su fundamento del corpus.\n\n"
    + CITATION_CONTRACT + "\n"
    "Claves del JSON: causales (lista de objetos con causal, procede [bool], "
    "fundamento [FUENTE: <id>], analisis), concurrencia_culpas (string), "
    "citas (lista de [FUENTE: <id>])."
)


def analyze_exoneration(facts: dict, retrieved: list, llm_fn: LLMFn | None = None) -> dict:
    """Evalúa las causales de exoneración aplicables a la defensa.

    Args:
        facts: Hechos estructurados (salida del Paso 2).
        retrieved: Fragmentos del corpus recuperados para este issue (con `id`).
        llm_fn: Función LLM a inyectar (para pruebas).

    Returns:
        Dict con `causales`, `concurrencia_culpas` y `citas`.
    """
    user = f"HECHOS:\n{facts}\n\nFRAGMENTOS DEL CORPUS:\n{format_chunks(retrieved)}"
    return run_json_step(_SYSTEM, user, llm_fn)
