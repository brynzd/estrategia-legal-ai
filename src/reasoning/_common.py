"""Utilidades comunes de los pasos de razonamiento.

Centraliza el contrato de citas (Restricciones duras #1 y #2), el formateo de los
fragmentos recuperados para el prompt y el parseo robusto de la respuesta JSON del
LLM. Así cada paso solo aporta su prompt específico.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..llm.client import LLMFn, get_default_llm

# Contrato que se inyecta en el system prompt de TODO paso que cita el corpus.
CITATION_CONTRACT = (
    "REGLAS DE CITA (obligatorias):\n"
    "- Cita ÚNICAMENTE con el formato [FUENTE: <id>], usando solo los id de los "
    "FRAGMENTOS proporcionados más abajo.\n"
    "- Está PROHIBIDO inventar fuentes, números de artículo, sentencias, fechas o "
    "doctrina. No uses conocimiento externo al de los fragmentos.\n"
    '- Si la información necesaria no está en los fragmentos, escribe exactamente: '
    '"No encontrado en el corpus".\n'
    "- Responde SOLO con un objeto JSON válido, sin texto adicional."
)


def format_chunks(retrieved: list) -> str:
    """Formatea los fragmentos recuperados para incluirlos en el prompt.

    Args:
        retrieved: Lista de objetos tipo `RetrievedChunk` (con `id`, `fuente`,
            `seccion`, `texto`).

    Returns:
        Texto con cada fragmento etiquetado por su `id`, listo para el prompt.
        Si no hay fragmentos, lo indica explícitamente.
    """
    if not retrieved:
        return "(No se recuperaron fragmentos del corpus para esta consulta.)"
    bloques = []
    for ch in retrieved:
        bloques.append(
            f"[id: {ch.id}] {ch.fuente} — {ch.seccion}\n{ch.texto}"
        )
    return "\n\n".join(bloques)


def parse_json(raw: str) -> dict[str, Any]:
    """Extrae un objeto JSON de la respuesta del LLM de forma robusta.

    Tolera que el modelo envuelva el JSON en vallas de código (```json ... ```) o
    lo acompañe de texto. Si no se puede parsear, devuelve el texto crudo bajo la
    clave `_unparsed` en vez de lanzar, para no romper el pipeline en runtime.

    Args:
        raw: Respuesta cruda del modelo.

    Returns:
        El objeto JSON como dict, o `{"_unparsed": raw}` si no se pudo parsear.
    """
    texto = raw.strip()
    valla = re.search(r"```(?:json)?\s*(\{.*\})\s*```", texto, re.DOTALL)
    if valla:
        texto = valla.group(1)
    else:
        ini, fin = texto.find("{"), texto.rfind("}")
        if ini != -1 and fin != -1 and fin > ini:
            texto = texto[ini : fin + 1]
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return {"_unparsed": raw}


def run_json_step(system: str, user: str, llm_fn: LLMFn | None = None) -> dict[str, Any]:
    """Ejecuta un paso que espera respuesta JSON del LLM.

    Args:
        system: System prompt del paso.
        user: Prompt de usuario (hechos + fragmentos).
        llm_fn: Función LLM a usar. Si es `None`, usa el proveedor por defecto.

    Returns:
        La respuesta del modelo parseada a dict (ver `parse_json`).
    """
    llm_fn = llm_fn or get_default_llm()
    return parse_json(llm_fn(system, user))
