"""Paso 3 — Clasificación de régimen de responsabilidad.

Usando `corpus/regimen_table.yaml` (autorada por los abogados), propone el régimen
aplicable (subjetiva culpa probada / subjetiva culpa presunta / objetiva) y las
normas aplicables, citando la base. Reconoce el matiz doctrinal cuando exista; no
afirma en seco. El código mapea hechos a las reglas que autoran los abogados; no
decide doctrina.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ..llm.client import LLMFn
from ._common import CITATION_CONTRACT, format_chunks, run_json_step

_SYSTEM = (
    "Eres un asistente jurídico (Colombia) que propone el RÉGIMEN de "
    "responsabilidad civil extracontractual a partir de una tabla de régimen "
    "autorada por abogados y de los fragmentos del corpus. No decides doctrina: "
    "aplicas la tabla y citas su base. Reconoce el matiz doctrinal cuando la tabla "
    "lo indique; no afirmes en seco.\n\n" + CITATION_CONTRACT + "\n"
    "Claves del JSON: regimen, normas (lista de id citados), matiz_doctrinal, "
    "razonamiento, citas (lista de [FUENTE: <id>])."
)


def classify_regime(
    facts: dict,
    regimen_table_path: Path,
    retrieved: list | None = None,
    llm_fn: LLMFn | None = None,
) -> dict:
    """Propone el régimen de responsabilidad y sus normas, con cita.

    Args:
        facts: Hechos estructurados (salida del Paso 2).
        regimen_table_path: Ruta a `corpus/regimen_table.yaml`.
        retrieved: Fragmentos del corpus recuperados (opcional, para respaldo
            jurisprudencial del matiz).
        llm_fn: Función LLM a inyectar (para pruebas).

    Returns:
        Dict con `regimen`, `normas`, `matiz_doctrinal`, `razonamiento` y `citas`.
    """
    tabla = Path(regimen_table_path).read_text(encoding="utf-8")
    # Se valida que el YAML sea legible; se pasa como texto al prompt.
    yaml.safe_load(tabla)

    user = (
        f"HECHOS:\n{facts}\n\n"
        f"TABLA DE RÉGIMEN (regimen_table.yaml):\n{tabla}\n\n"
        f"FRAGMENTOS DEL CORPUS:\n{format_chunks(retrieved or [])}"
    )
    return run_json_step(_SYSTEM, user, llm_fn)
