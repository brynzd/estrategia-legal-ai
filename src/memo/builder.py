"""Paso 6 — Ensamblado del memorando de estrategia defensiva (híbrido).

Estrategia híbrida (estructura determinista + redacción por sección con LLM):

  - El CÓDIGO decide la estructura y el ORDEN por solidez: lee las salidas ya
    fundamentadas de cada paso de razonamiento (`AnalysisResult`), evalúa la
    solidez de cada argumento según los criterios de `corpus/rubrica_solidez.md`
    (apoyo normativo, respaldo, soporte probatorio, efecto procesal) y ordena de
    más a menos sólido. Así el orden es trazable y no depende del LLM.

  - El LLM solo REDACTA la prosa de cada sección, y SOLO con el material de esa
    sección (su análisis + los fragmentos recuperados para ese issue). No se le
    permite introducir citas nuevas: se le pasa la lista de ids citables y el
    contrato de citas. La validación global (`src/memo/validator.py`) atrapa
    cualquier cita huérfana como red de seguridad (Restricciones duras #1 y #2).

Cada sección redactada se registra en el `Tracer` para el panel de trazabilidad.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import config
from ..llm.client import LLMFn, get_default_llm
from ..reasoning._common import format_chunks
from ..reasoning.analyze import AnalysisResult
from ..trace import Tracer
from .validator import extract_citations

DISCLAIMER: str = (
    "Este documento es un apoyo a la decisión generado de forma asistida. "
    "No constituye asesoría legal autónoma y no sustituye el criterio del "
    "abogado, quien debe validar cada cita y conclusión contra la fuente oficial."
)

# Secciones argumentativas que se ordenan por solidez: (clave de retrieved,
# título, atributo de AnalysisResult con la salida del paso).
_ARG_SECCIONES: list[tuple[str, str, str]] = [
    ("nexo_causal", "Nexo causal", "causation"),
    ("exoneracion", "Causales de exoneración", "exoneration"),
    ("perjuicio", "Perjuicio", "damages"),
    ("terceros", "Vinculación de terceros", "third_parties"),
]

# Contrato de redacción: como el de citas de los pasos, pero pide PROSA (no JSON).
_REDACCION_SYSTEM: str = (
    "Eres un asistente jurídico (Colombia) que REDACTA una sección de un memorando "
    "de estrategia defensiva en responsabilidad civil extracontractual. Escribe en "
    "prosa jurídica clara y concisa (markdown, sin encabezados), usando "
    "EXCLUSIVAMENTE el material que se te entrega.\n"
    "- Cita con el formato [FUENTE: <id>] y SOLO los ids listados como citables.\n"
    "- Está PROHIBIDO inventar hechos, fuentes, números, sentencias o doctrina "
    "fuera del material.\n"
    f'- Si el material no sustenta algo, escríbelo: "{config.NOT_FOUND_SENTINEL}".\n'
    "- No devuelvas JSON; devuelve solo la prosa de la sección."
)


def _bonus_efecto_procesal(clave: str, analysis: dict) -> int:
    """Bonus de solidez por efecto procesal (criterio 5 de la rúbrica).

    Premia los argumentos de mayor impacto para la defensa: una exoneración que
    procede (exonera total o parcialmente) o un ataque al quantum cuando un rubro
    del perjuicio no está soportado.

    Args:
        clave: Clave del issue (`nexo_causal`, `exoneracion`, `perjuicio`, ...).
        analysis: Salida del paso de razonamiento correspondiente.

    Returns:
        1 si el argumento tiene efecto procesal relevante, 0 en caso contrario.
    """
    if clave == "exoneracion":
        causales = analysis.get("causales") or []
        if any(isinstance(c, dict) and c.get("procede") for c in causales):
            return 1
    if clave == "perjuicio":
        for rubro in ("dano_emergente", "lucro_cesante"):
            valor = analysis.get(rubro)
            if isinstance(valor, dict) and valor.get("soportado") is False:
                return 1
    return 0


def score_solidez(clave: str, analysis: dict) -> tuple[str, int]:
    """Evalúa la solidez de un argumento según la rúbrica (de más a menos sólido).

    Heurística de andamiaje (los pesos los afinan los abogados, ver
    `rubrica_solidez.md`): suma el apoyo en fuentes citadas, penaliza la ausencia
    de sustento ("No encontrado en el corpus") y premia el efecto procesal.

    Args:
        clave: Clave del issue.
        analysis: Salida del paso de razonamiento (con su lista `citas`).

    Returns:
        Tupla `(nivel, puntaje)` con nivel en {"ALTA", "MEDIA", "BAJA"}.
    """
    texto = json.dumps(analysis, ensure_ascii=False)
    citas = analysis.get("citas") or []
    ids = extract_citations(" ".join(citas)) if citas else extract_citations(texto)

    puntaje = len(ids)
    if config.NOT_FOUND_SENTINEL.lower() in texto.lower():
        puntaje -= 1
    puntaje += _bonus_efecto_procesal(clave, analysis)

    nivel = "ALTA" if puntaje >= 2 else "MEDIA" if puntaje == 1 else "BAJA"
    return nivel, puntaje


def _redactar_seccion(
    titulo: str,
    nivel: str,
    analysis: dict,
    fragmentos: list,
    facts: dict,
    llm_fn: LLMFn,
) -> str:
    """Redacta la prosa de una sección con el LLM, acotada a su material.

    Args:
        titulo: Título de la sección.
        nivel: Nivel de solidez evaluado ("ALTA"/"MEDIA"/"BAJA" o "—" para encuadre).
        analysis: Salida del paso de razonamiento de la sección.
        fragmentos: Fragmentos del corpus recuperados para el issue (con `id`).
        facts: Hechos del caso (para situar la redacción).
        llm_fn: Función LLM a usar.

    Returns:
        La prosa de la sección (markdown), con citas solo de los ids permitidos.
    """
    ids_analisis = extract_citations(" ".join(analysis.get("citas") or []))
    ids_citables = sorted({c.id for c in fragmentos} | set(ids_analisis))

    user = (
        f"SECCIÓN: {titulo} (solidez evaluada: {nivel})\n\n"
        f"HECHOS DEL CASO:\n{json.dumps(facts, ensure_ascii=False)}\n\n"
        f"MATERIAL DEL ANÁLISIS (JSON):\n{json.dumps(analysis, ensure_ascii=False, indent=2)}\n\n"
        f"FRAGMENTOS DEL CORPUS:\n{format_chunks(fragmentos)}\n\n"
        f"IDS QUE PUEDES CITAR EN ESTA SECCIÓN: {ids_citables}"
    )
    return llm_fn(_REDACCION_SYSTEM, user).strip()


def build_memo(
    result: AnalysisResult,
    rubrica_path: Path,
    *,
    llm_fn: LLMFn | None = None,
    tracer: Tracer | None = None,
) -> str:
    """Ensambla el memorando final a partir de la fase de razonamiento.

    El encuadre (hechos + régimen) abre el memorando como marco; los cuatro
    argumentos de defensa se ordenan de más a menos sólido según la rúbrica. Cada
    sección la redacta el LLM con su propio material (híbrido). El resultado pasa
    luego por la validación de citas en el pipeline.

    Args:
        result: Salidas de la fase de razonamiento (ver `reasoning.analyze`).
        rubrica_path: Ruta a `rubrica_solidez.md` cuyos criterios implementa
            `score_solidez`; se registra en la traza del ordenamiento.
        llm_fn: Función LLM a inyectar (para pruebas). Si es `None`, usa el
            proveedor por defecto.
        tracer: Acumulador de trazas. Si es `None`, se crea uno interno.

    Returns:
        El memorando en markdown: título, disclaimer, encuadre y argumentos
        ordenados por solidez, con citas `[FUENTE: <id>]`.
    """
    llm_fn = llm_fn or get_default_llm()
    tracer = tracer or Tracer()

    # Encuadre del caso + régimen aplicable (marco; no se ordena por solidez).
    encuadre = _redactar_seccion(
        "Encuadre del caso y régimen aplicable", "—",
        result.regime, result.retrieved.get("regimen", []), result.facts, llm_fn,
    )
    tracer.record("memo:encuadre", entrada={"regimen": result.regime.get("regimen")}, salida=encuadre)

    # Evaluar solidez de cada argumento y ordenar de más a menos sólido.
    evaluados = []
    for clave, titulo, attr in _ARG_SECCIONES:
        analysis = getattr(result, attr)
        nivel, puntaje = score_solidez(clave, analysis)
        evaluados.append((puntaje, nivel, clave, titulo, analysis))
    evaluados.sort(key=lambda x: x[0], reverse=True)
    tracer.record(
        "memo:orden_solidez",
        entrada={"rubrica": str(rubrica_path)},
        salida=[(titulo, nivel) for _, nivel, _, titulo, _ in evaluados],
    )

    # Redactar cada argumento en orden de solidez.
    secciones_md = []
    for i, (_, nivel, clave, titulo, analysis) in enumerate(evaluados, start=1):
        prosa = _redactar_seccion(
            titulo, nivel, analysis, result.retrieved.get(clave, []), result.facts, llm_fn,
        )
        secciones_md.append(f"### {i}. {titulo} — solidez {nivel}\n\n{prosa}")
        tracer.record(f"memo:{clave}", entrada={"nivel": nivel}, salida=prosa)

    partes = [
        "# Memorando de estrategia defensiva — Responsabilidad Civil Extracontractual",
        f"> {DISCLAIMER}",
        "## Encuadre del caso y régimen aplicable",
        encuadre,
        "## Argumentos de defensa (ordenados por solidez)",
        *secciones_md,
    ]
    return "\n\n".join(partes)
