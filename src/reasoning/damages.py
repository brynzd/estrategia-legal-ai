"""Paso 5 — Perjuicio (daño emergente y lucro cesante).

Revisa si el daño emergente y el lucro cesante reclamados están soportados y
propone pruebas de descargo concretas. Para casos de tránsito, contrasta el
quantum con la tabla SOAT (Decreto 056/2015) si está en el corpus.
"""

from __future__ import annotations

from ..llm.client import LLMFn
from ._common import CITATION_CONTRACT, format_chunks, run_json_step

_SYSTEM = (
    "Eres un asistente jurídico (Colombia) que analiza el PERJUICIO en "
    "responsabilidad civil extracontractual desde la defensa: revisa si el daño "
    "emergente y el lucro cesante reclamados están soportados, contrasta el quantum "
    "con la tabla SOAT si aparece en el corpus, y propone pruebas de descargo "
    "concretas.\n\n" + CITATION_CONTRACT + "\n"
    "Claves del JSON: dano_emergente (objeto con soportado [bool] y analisis), "
    "lucro_cesante (objeto con soportado [bool] y analisis), contraste_soat (string), "
    "pruebas_descargo (lista), citas (lista de [FUENTE: <id>])."
)


def analyze_damages(facts: dict, retrieved: list, llm_fn: LLMFn | None = None) -> dict:
    """Analiza la procedencia y el soporte probatorio de los perjuicios.

    Args:
        facts: Hechos estructurados (salida del Paso 2), incluidos los daños
            reclamados y las pruebas aportadas.
        retrieved: Fragmentos del corpus recuperados (incluida la tabla SOAT si
            aplica), con su `id`.
        llm_fn: Función LLM a inyectar (para pruebas).

    Returns:
        Dict con `dano_emergente`, `lucro_cesante`, `contraste_soat`,
        `pruebas_descargo` y `citas`.
    """
    user = f"HECHOS:\n{facts}\n\nFRAGMENTOS DEL CORPUS:\n{format_chunks(retrieved)}"
    return run_json_step(_SYSTEM, user, llm_fn)
