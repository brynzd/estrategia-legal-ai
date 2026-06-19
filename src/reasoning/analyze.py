"""Paso 4 + 5 — Recuperación RAG por issue y orquestación del razonamiento.

Este módulo es el "pegamento" que faltaba en la Fase 2: encadena el encuadre del
caso, la clasificación de régimen, la recuperación de fragmentos del corpus por
cada issue jurídico y los cuatro pasos de razonamiento (nexo causal, exoneración,
perjuicio y vinculación de terceros), dejando una traza por paso.

Frontera con la Fase 3: aquí termina el RAZONAMIENTO y se produce un
`AnalysisResult`. El ensamblado del memorando (`src/memo/builder.py`) y la
validación de citas (`src/memo/validator.py`) consumen ese resultado, pero NO se
implementan aquí.

Restricciones duras respetadas:
  #1/#2  Cada paso de razonamiento solo recibe los fragmentos efectivamente
         recuperados del corpus; las consultas son términos de búsqueda, no
         afirmaciones de fuentes. Lo que no esté en el corpus el paso lo reporta
         como "No encontrado en el corpus".
  #3     Cada paso (encuadre, régimen, recuperación por issue y los cuatro
         análisis) se registra en un `Tracer` con su entrada y su salida.
  #5     El código NO decide doctrina: mapea hechos a consultas y delega en los
         pasos, que citan la base autorada por los abogados.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .. import config
from ..llm.client import LLMFn
from ..rag.retriever import RetrievedChunk, retrieve
from ..trace import StepTrace, Tracer
from .case_framing import frame_case
from .causation import analyze_causation
from .damages import analyze_damages
from .exoneration import analyze_exoneration
from .regime import classify_regime
from .third_parties import analyze_third_parties

# Una RetrieveFn recibe una consulta y devuelve los fragmentos recuperados del
# corpus. Se inyecta para poder probar sin descargar modelos ni leer disco; por
# defecto usa `src.rag.retriever.retrieve` sobre el índice configurado.
from typing import Callable

RetrieveFn = Callable[[str], list[RetrievedChunk]]

# Frase de búsqueda por tipo de hecho. Son TÉRMINOS DE BÚSQUEDA (no citas ni
# doctrina): enfocan la recuperación hacia el área del caso. Si el corpus no
# contiene la fuente, el paso de razonamiento lo dirá ("No encontrado en el corpus").
_TIPO_FRASE: dict[str, str] = {
    "transito": "accidente de tránsito por conducción de vehículos",
    "actividad_peligrosa": "daño causado por actividad peligrosa",
    "medica": "responsabilidad médica por la atención en salud",
    "producto": "daño causado por producto defectuoso",
    "otro": "responsabilidad civil extracontractual",
}


def build_issue_queries(facts: dict) -> dict[str, str]:
    """Construye las consultas de recuperación por issue a partir de los hechos.

    A cada issue jurídico (régimen y los cuatro pasos de razonamiento) le
    corresponde una consulta en español jurídico, enfocada por el tipo de hecho
    encuadrado. Para tránsito se añade el contraste con la tabla SOAT en el issue
    de perjuicio (ver CLAUDE.md, paso 5).

    Args:
        facts: Hechos estructurados (salida del encuadre). Se usa `tipo_hecho`
            para enfocar las consultas; si falta, se asume "otro".

    Returns:
        Dict con una consulta por clave: `regimen`, `nexo_causal`, `exoneracion`,
        `perjuicio`, `terceros`.
    """
    tipo = (facts.get("tipo_hecho") or "otro").lower()
    frase = _TIPO_FRASE.get(tipo, _TIPO_FRASE["otro"])

    perjuicio = (
        f"perjuicios daño emergente lucro cesante prueba del quantum en {frase}"
    )
    if tipo == "transito":
        perjuicio += " tabla SOAT seguro obligatorio de accidentes de tránsito"

    return {
        "regimen": f"régimen de responsabilidad civil extracontractual aplicable a {frase}",
        "nexo_causal": f"nexo causal relación de causalidad entre la conducta y el daño en {frase}",
        "exoneracion": (
            "causales de exoneración culpa exclusiva de la víctima hecho de un "
            f"tercero fuerza mayor concurrencia de culpas en {frase}"
        ),
        "perjuicio": perjuicio,
        "terceros": (
            "vinculación de terceros llamamiento en garantía aseguradora denuncia "
            f"del pleito en {frase}"
        ),
    }


@dataclass
class AnalysisResult:
    """Resultado de la fase de razonamiento (Paso 4 + 5).

    Reúne las salidas de todos los pasos de razonamiento más los fragmentos
    recuperados por issue (para el panel de trazabilidad) y las trazas registradas.
    Lo consume la Fase 3 (ensamblado del memorando y validación de citas).

    Attributes:
        facts: Hechos estructurados (encuadre del caso).
        regime: Clasificación de régimen (con cita de su base).
        causation: Análisis del nexo causal.
        exoneration: Análisis de causales de exoneración.
        damages: Análisis de perjuicio (con contraste SOAT si aplica).
        third_parties: Sugerencia de vinculación de terceros.
        retrieved: Fragmentos recuperados por issue (clave -> lista de chunks).
        traces: Pasos registrados, en orden de ejecución.
    """

    facts: dict
    regime: dict
    causation: dict
    exoneration: dict
    damages: dict
    third_parties: dict
    retrieved: dict[str, list[RetrievedChunk]] = field(default_factory=dict)
    traces: list[StepTrace] = field(default_factory=list)


def _default_retrieve_fn(query: str) -> list[RetrievedChunk]:
    """RetrieveFn por defecto: recupera del índice configurado en `config`."""
    return retrieve(query)


def run_analysis(
    demanda_text: str,
    *,
    regimen_table_path: Path | None = None,
    retrieve_fn: RetrieveFn | None = None,
    llm_fn: LLMFn | None = None,
    tracer: Tracer | None = None,
    issue_queries: dict[str, str] | None = None,
) -> AnalysisResult:
    """Ejecuta la fase de razonamiento de extremo a extremo sobre la demanda.

    Encadena: encuadre del caso -> recuperación por issue -> clasificación de
    régimen -> nexo causal -> exoneración -> perjuicio -> vinculación de terceros.
    Cada paso se registra en el `tracer` para el panel de trazabilidad.

    Args:
        demanda_text: Texto plano de la demanda (salida del Paso 1, extracción).
        regimen_table_path: Ruta a `regimen_table.yaml`. Si es `None`, usa
            `config.REGIMEN_TABLE_PATH`.
        retrieve_fn: Función de recuperación `query -> [RetrievedChunk]`. Si es
            `None`, usa el índice configurado. Inyectable para pruebas.
        llm_fn: Función LLM a inyectar en todos los pasos. Si es `None`, cada paso
            usa el proveedor por defecto.
        tracer: Acumulador de trazas. Si es `None`, se crea uno nuevo y sus pasos
            quedan en `AnalysisResult.traces`.
        issue_queries: Consultas de recuperación por issue. Si es `None`, se
            derivan de los hechos con `build_issue_queries`.

    Returns:
        Un `AnalysisResult` con las salidas de cada paso, los fragmentos
        recuperados por issue y las trazas.
    """
    regimen_table_path = regimen_table_path or config.REGIMEN_TABLE_PATH
    retrieve_fn = retrieve_fn or _default_retrieve_fn
    tracer = tracer or Tracer()

    # Paso 2 — Encuadre del caso (texto de la demanda -> hechos estructurados).
    facts = frame_case(demanda_text, llm_fn)
    tracer.record("encuadre_caso", entrada={"demanda_text": demanda_text}, salida=facts)

    # Paso 4 — Recuperación RAG por issue. Las consultas se derivan de los hechos.
    queries = issue_queries or build_issue_queries(facts)
    retrieved: dict[str, list[RetrievedChunk]] = {}
    for issue, query in queries.items():
        chunks = retrieve_fn(query)
        retrieved[issue] = chunks
        tracer.record(
            f"recuperacion:{issue}",
            entrada={"query": query},
            salida=[c.id for c in chunks],  # ids recuperados (trazabilidad)
        )

    # Paso 3 — Clasificación de régimen (con la tabla y el respaldo recuperado).
    regime = classify_regime(facts, regimen_table_path, retrieved["regimen"], llm_fn)
    tracer.record("clasificacion_regimen", entrada=facts, salida=regime)

    # Paso 5 — Razonamiento por issue. Cada paso solo cita lo recuperado para él.
    causation = analyze_causation(facts, retrieved["nexo_causal"], llm_fn)
    tracer.record("nexo_causal", entrada={"chunks": [c.id for c in retrieved["nexo_causal"]]}, salida=causation)

    exoneration = analyze_exoneration(facts, retrieved["exoneracion"], llm_fn)
    tracer.record("exoneracion", entrada={"chunks": [c.id for c in retrieved["exoneracion"]]}, salida=exoneration)

    damages = analyze_damages(facts, retrieved["perjuicio"], llm_fn)
    tracer.record("perjuicio", entrada={"chunks": [c.id for c in retrieved["perjuicio"]]}, salida=damages)

    third_parties = analyze_third_parties(facts, retrieved["terceros"], llm_fn)
    tracer.record("terceros", entrada={"chunks": [c.id for c in retrieved["terceros"]]}, salida=third_parties)

    return AnalysisResult(
        facts=facts,
        regime=regime,
        causation=causation,
        exoneration=exoneration,
        damages=damages,
        third_parties=third_parties,
        retrieved=retrieved,
        traces=tracer.steps,
    )
