"""Trazabilidad del pipeline (Restricción dura #3).

Cada paso del pipeline (2–6) registra su entrada y su salida para mostrarse en el
panel de trazabilidad de la UI. Este módulo ofrece un acumulador simple de pasos;
no decide nada jurídico, solo deja rastro de cómo se llegó a cada conclusión.

Uso típico:
    tracer = Tracer()
    tracer.record("clasificacion_regimen", entrada=hechos, salida=regimen)
    ...
    for paso in tracer.steps:
        print(paso.name, paso.output)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger("estrategia_legal")


@dataclass
class StepTrace:
    """Registro de un paso del pipeline.

    Attributes:
        name: Identificador del paso (p. ej. "nexo_causal").
        input: Entrada que recibió el paso (hechos, consulta, etc.).
        output: Salida producida por el paso.
        timestamp: Momento en que se registró el paso (ISO 8601).
    """

    name: str
    input: Any
    output: Any
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class Tracer:
    """Acumula los `StepTrace` de una ejecución del pipeline."""

    def __init__(self) -> None:
        """Inicializa un tracer vacío."""
        self.steps: list[StepTrace] = []

    def record(self, name: str, entrada: Any, salida: Any) -> StepTrace:
        """Registra un paso del pipeline y lo deja también en el log.

        Args:
            name: Identificador del paso.
            entrada: Entrada que recibió el paso.
            salida: Salida producida por el paso.

        Returns:
            El `StepTrace` recién creado y añadido a `self.steps`.
        """
        step = StepTrace(name=name, input=entrada, output=salida)
        self.steps.append(step)
        logger.info("paso=%s registrado", name)
        return step
