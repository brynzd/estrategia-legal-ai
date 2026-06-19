"""Paso 5 — Nexo causal.

Identifica los elementos del nexo causal sobre los hechos del caso, fundamentando
cada afirmación en los fragmentos recuperados del corpus. Señala dónde el vínculo
causal es débil o discutible para la defensa.
"""

from __future__ import annotations

from ..llm.client import LLMFn
from ._common import CITATION_CONTRACT, format_chunks, run_json_step

_SYSTEM = (
    "Eres un asistente jurídico (Colombia) que analiza el NEXO CAUSAL entre la "
    "conducta y el daño en un caso de responsabilidad civil extracontractual, "
    "desde la perspectiva de la DEFENSA. Fundamenta cada afirmación en los "
    "fragmentos del corpus y señala los puntos débiles del nexo para la defensa.\n\n"
    + CITATION_CONTRACT + "\n"
    "Claves del JSON: elementos (lista), puntos_debiles_defensa (lista), "
    "razonamiento, citas (lista de [FUENTE: <id>])."
)


def analyze_causation(facts: dict, retrieved: list, llm_fn: LLMFn | None = None) -> dict:
    """Analiza el nexo causal entre la conducta y el daño.

    Args:
        facts: Hechos estructurados (salida del Paso 2).
        retrieved: Fragmentos del corpus recuperados para este issue (con `id`).
        llm_fn: Función LLM a inyectar (para pruebas).

    Returns:
        Dict con `elementos`, `puntos_debiles_defensa`, `razonamiento` y `citas`.
    """
    user = f"HECHOS:\n{facts}\n\nFRAGMENTOS DEL CORPUS:\n{format_chunks(retrieved)}"
    return run_json_step(_SYSTEM, user, llm_fn)
