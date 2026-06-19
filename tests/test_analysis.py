"""Tests de la orquestación del razonamiento (Fase 2 — Paso 4 + 5).

Demuestran la DoD de la Fase 2 SIN red ni API ni descarga de modelos:
- el orquestador recupera fragmentos del corpus por cada issue y se los pasa al
  paso de razonamiento correspondiente (el id recuperado llega al prompt),
- registra una traza por paso (Restricción dura #3),
- y las citas que emiten los pasos son válidas contra el corpus (Restricción dura
  #2): no hay citas huérfanas ("sin citas inventadas").

Se usan el corpus_demo neutro (no jurídico) de los fixtures, un embedder simulado
determinista y un LLM enrutado por el system prompt de cada paso.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path

import numpy as np

from src.memo.validator import load_corpus_ids, validate_citations
from src.rag.ingest import build_index
from src.rag.retriever import retrieve
from src.reasoning.analyze import build_issue_queries, run_analysis

FIXTURE = Path(__file__).parent / "fixtures" / "corpus_demo"

# Mismo embedder simulado que test_retrieval: cada texto -> vector de presencia de
# estos términos, L2-normalizado. Textos del mismo tema quedan cerca en coseno.
_VOCAB = ["fruta", "cocina", "auto", "carretera", "musica", "concierto"]


def mock_embed(texts: list[str]) -> np.ndarray:
    filas = []
    for t in texts:
        tl = t.lower()
        v = np.array([1.0 if term in tl else 0.0 for term in _VOCAB], dtype=np.float32)
        norm = np.linalg.norm(v)
        filas.append(v / norm if norm > 0 else v)
    return np.vstack(filas)


class RoutingFakeLLM:
    """LLM simulado: enruta por un substring del system prompt y registra llamadas.

    Cada ruta es (substring_esperado_en_system, respuesta_json). Permite devolver
    una respuesta distinta por paso de razonamiento sin gastar API.
    """

    def __init__(self, rutas: list[tuple[str, str]]) -> None:
        self.rutas = rutas
        self.calls: list[tuple[str, str]] = []

    def __call__(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        for substring, respuesta in self.rutas:
            if substring in system:
                return respuesta
        return "{}"

    def user_de(self, substring_system: str) -> str:
        """Devuelve el `user` de la primera llamada cuyo system contiene el substring."""
        for system, user in self.calls:
            if substring_system in system:
                return user
        return ""


# Respuestas por paso. Cada una cita ids que SÍ existen en el corpus_demo
# (demo_alpha / demo_beta / demo_gamma): así no debe haber citas huérfanas.
_RUTAS = [
    ("HECHOS estructurados",
     '{"tipo_hecho": "transito", "partes": {}, "hechos": [], '
     '"danos_reclamados": [], "pruebas_aportadas": []}'),
    ("RÉGIMEN",
     '{"regimen": "objetiva", "normas": ["demo_beta"], "matiz_doctrinal": "", '
     '"razonamiento": "r", "citas": ["[FUENTE: demo_beta]"]}'),
    ("NEXO CAUSAL",
     '{"elementos": [], "puntos_debiles_defensa": [], "razonamiento": "r", '
     '"citas": ["[FUENTE: demo_beta]"]}'),
    ("CAUSALES DE EXONERACIÓN",
     '{"causales": [], "concurrencia_culpas": "", "citas": ["[FUENTE: demo_alpha]"]}'),
    ("PERJUICIO",
     '{"dano_emergente": {"soportado": false, "analisis": ""}, '
     '"lucro_cesante": {"soportado": false, "analisis": ""}, "contraste_soat": "", '
     '"pruebas_descargo": [], "citas": ["[FUENTE: demo_gamma]"]}'),
    ("VINCULACIÓN DE TERCEROS",
     '{"figuras": [], "citas": ["[FUENTE: demo_beta]"]}'),
]

# Consultas con vocabulario del embedder simulado, una por issue, para que la
# recuperación real (retrieve) traiga el chunk correcto del corpus_demo.
_ISSUE_QUERIES = {
    "regimen": "auto en la carretera",        # -> demo_beta
    "nexo_causal": "auto carretera",          # -> demo_beta
    "exoneracion": "fruta en la cocina",      # -> demo_alpha
    "perjuicio": "musica concierto",          # -> demo_gamma
    "terceros": "auto carretera",             # -> demo_beta
}


# --- build_issue_queries (unitario, sin red) --------------------------------

def test_build_issue_queries_tiene_las_cinco_claves():
    queries = build_issue_queries({"tipo_hecho": "transito"})
    assert set(queries) == {"regimen", "nexo_causal", "exoneracion", "perjuicio", "terceros"}
    assert all(q.strip() for q in queries.values())


def test_build_issue_queries_transito_contrasta_soat():
    queries = build_issue_queries({"tipo_hecho": "transito"})
    assert "SOAT" in queries["perjuicio"]


def test_build_issue_queries_no_transito_sin_soat():
    queries = build_issue_queries({"tipo_hecho": "medica"})
    assert "SOAT" not in queries["perjuicio"]


def test_build_issue_queries_producto_enfoca_el_tipo():
    # Fase 5: el motor generaliza a producto sin cambios de código.
    queries = build_issue_queries({"tipo_hecho": "producto"})
    assert "SOAT" not in queries["perjuicio"]
    assert "producto" in queries["regimen"].lower()


def test_build_issue_queries_medica_enfoca_el_tipo():
    # Fase 5: el motor generaliza a responsabilidad médica sin cambios de código.
    queries = build_issue_queries({"tipo_hecho": "medica"})
    regimen = queries["regimen"].lower()
    assert "médica" in regimen or "salud" in regimen


def test_build_issue_queries_sin_tipo_usa_otro():
    # No debe lanzar si faltan los hechos; cae en "otro".
    queries = build_issue_queries({})
    assert set(queries) == {"regimen", "nexo_causal", "exoneracion", "perjuicio", "terceros"}


# --- run_analysis (integración con retrieve real + LLM simulado) ------------

def _retrieve_fn(tmp_path: Path):
    build_index(FIXTURE, tmp_path / "idx", embed_fn=mock_embed)
    return partial(retrieve, index_dir=tmp_path / "idx", embed_fn=mock_embed, top_k=1)


def test_run_analysis_encadena_todos_los_pasos(tmp_path):
    fake = RoutingFakeLLM(_RUTAS)
    res = run_analysis(
        "Texto de la demanda de tránsito...",
        retrieve_fn=_retrieve_fn(tmp_path),
        llm_fn=fake,
        issue_queries=_ISSUE_QUERIES,
    )

    # Cada paso produjo salida parseada (no quedó como texto sin parsear).
    assert res.facts["tipo_hecho"] == "transito"
    assert res.regime["regimen"] == "objetiva"
    for salida in (res.causation, res.exoneration, res.damages, res.third_parties):
        assert "_unparsed" not in salida


def test_run_analysis_recupera_por_issue_y_alimenta_los_pasos(tmp_path):
    fake = RoutingFakeLLM(_RUTAS)
    res = run_analysis(
        "Texto de la demanda...",
        retrieve_fn=_retrieve_fn(tmp_path),
        llm_fn=fake,
        issue_queries=_ISSUE_QUERIES,
    )

    # La recuperación por issue trajo el fragmento correcto del corpus_demo.
    assert res.retrieved["perjuicio"][0].id == "demo_gamma"
    assert res.retrieved["exoneracion"][0].id == "demo_alpha"
    assert res.retrieved["regimen"][0].id == "demo_beta"

    # El id recuperado para el perjuicio llegó al prompt de ese paso (pegamento RAG).
    assert "demo_gamma" in fake.user_de("PERJUICIO")


def test_run_analysis_registra_una_traza_por_paso(tmp_path):
    fake = RoutingFakeLLM(_RUTAS)
    res = run_analysis(
        "Texto de la demanda...",
        retrieve_fn=_retrieve_fn(tmp_path),
        llm_fn=fake,
        issue_queries=_ISSUE_QUERIES,
    )

    nombres = {t.name for t in res.traces}
    assert {"encuadre_caso", "clasificacion_regimen", "nexo_causal",
            "exoneracion", "perjuicio", "terceros"} <= nombres
    # También se traza la recuperación de cada issue.
    assert "recuperacion:perjuicio" in nombres


def test_run_analysis_no_produce_citas_huerfanas(tmp_path):
    """DoD Fase 2: salida citada y SIN citas inventadas (Restricción dura #2)."""
    fake = RoutingFakeLLM(_RUTAS)
    res = run_analysis(
        "Texto de la demanda...",
        retrieve_fn=_retrieve_fn(tmp_path),
        llm_fn=fake,
        issue_queries=_ISSUE_QUERIES,
    )

    # Junta todas las citas emitidas por los pasos y valida contra el corpus real.
    citas = []
    for salida in (res.regime, res.causation, res.exoneration, res.damages, res.third_parties):
        citas.extend(salida.get("citas", []))
    texto = " ".join(citas)

    reporte = validate_citations(texto, load_corpus_ids(FIXTURE))
    assert reporte.cited_ids, "el caso de prueba debe emitir al menos una cita"
    assert reporte.is_valid
    assert reporte.orphan_ids == []
