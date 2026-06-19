"""Paso 2 — Encuadre del caso (PDF -> JSON de hechos estructurados).

Con ayuda del LLM, extrae del texto de la demanda los hechos estructurados: tipo
de hecho (tránsito / actividad peligrosa / médica / producto), daños reclamados,
pruebas aportadas y partes. No infiere doctrina ni cita corpus; solo organiza lo
que dice la demanda. No inventa datos que no estén en el texto.
"""

from __future__ import annotations

from ..llm.client import LLMFn
from ._common import run_json_step

_SYSTEM = (
    "Eres un asistente jurídico que extrae HECHOS estructurados de una demanda de "
    "responsabilidad civil extracontractual (Colombia). Extrae SOLO lo que la "
    "demanda afirma; no inventes datos, no interpretes doctrina ni anticipes "
    "conclusiones. Si un dato no aparece, usa null o una lista vacía. "
    "Responde SOLO con un objeto JSON válido con estas claves: "
    "tipo_hecho (uno de: transito, actividad_peligrosa, medica, producto, otro), "
    "partes (objeto con demandante y demandado), "
    "hechos (lista de strings), "
    "danos_reclamados (lista de strings), "
    "pruebas_aportadas (lista de strings)."
)


def frame_case(demanda_text: str, llm_fn: LLMFn | None = None) -> dict:
    """Extrae los hechos estructurados de la demanda.

    Args:
        demanda_text: Texto plano de la demanda (salida del Paso 1).
        llm_fn: Función LLM a inyectar (para pruebas). Si es `None`, usa el
            proveedor configurado por defecto.

    Returns:
        Dict con los hechos estructurados: `tipo_hecho`, `partes`, `hechos`,
        `danos_reclamados`, `pruebas_aportadas`.
    """
    user = f"DEMANDA:\n{demanda_text}"
    return run_json_step(_SYSTEM, user, llm_fn)
