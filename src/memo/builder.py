"""Paso 6 — Ensamblado del memorando de estrategia defensiva.

Con ayuda del LLM, ensambla las salidas de los pasos de razonamiento en un
memorando estructurado por secciones. Ordena los argumentos de más a menos sólido
según `corpus/rubrica_solidez.md`, mantiene la cita `[FUENTE: <id>]` en cada
afirmación e incluye el disclaimer de que es un documento de apoyo que no sustituye
el criterio del abogado.

Pendiente de implementar — ver Fase 3 del PLAN.md.
"""

from __future__ import annotations

from pathlib import Path

DISCLAIMER: str = (
    "Este documento es un apoyo a la decisión generado de forma asistida. "
    "No constituye asesoría legal autónoma y no sustituye el criterio del "
    "abogado, quien debe validar cada cita y conclusión contra la fuente oficial."
)


def build_memo(analyses: dict, rubrica_path: Path) -> str:
    """Ensambla el memorando final a partir de los pasos de razonamiento.

    Args:
        analyses: Salidas de los pasos de razonamiento (régimen, nexo causal,
            exoneración, perjuicio, vinculación de terceros).
        rubrica_path: Ruta a `corpus/rubrica_solidez.md` para ordenar argumentos.

    Returns:
        El memorando en texto (markdown), con argumentos ordenados por solidez,
        citas `[FUENTE: <id>]` y el disclaimer de documento de apoyo.
    """
    raise NotImplementedError("Fase 3 del PLAN.md — ensamblado del memorando.")
