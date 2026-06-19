"""Tests de los pasos de razonamiento (Fase 2).

Usan un LLM SIMULADO (espía) para validar, sin gastar API ni clave:
- el parseo robusto de la respuesta JSON,
- el formateo de los fragmentos recuperados,
- que el contrato de citas viaja en el system prompt,
- que cada paso devuelve la estructura esperada.
"""

from __future__ import annotations

import pytest

from src import config
from src.rag.retriever import RetrievedChunk
from src.reasoning._common import CITATION_CONTRACT, format_chunks, parse_json
from src.reasoning.case_framing import frame_case
from src.reasoning.causation import analyze_causation
from src.reasoning.damages import analyze_damages
from src.reasoning.exoneration import analyze_exoneration
from src.reasoning.regime import classify_regime
from src.reasoning.third_parties import analyze_third_parties


class SpyLLM:
    """LLM simulado: registra (system, user) recibidos y devuelve una respuesta fija."""

    def __init__(self, respuesta: str) -> None:
        self.respuesta = respuesta
        self.system: str | None = None
        self.user: str | None = None

    def __call__(self, system: str, user: str) -> str:
        self.system, self.user = system, user
        return self.respuesta


def _chunk(cid: str) -> RetrievedChunk:
    return RetrievedChunk(
        id=cid, texto=f"texto de {cid}", fuente="Fuente X", seccion="Art. 1",
        url="https://example.com", score=0.9,
    )


# --- parse_json -------------------------------------------------------------

def test_parse_json_directo():
    assert parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_con_vallas_de_codigo():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_con_texto_alrededor():
    assert parse_json('Claro, aquí está: {"a": 1}. Listo.') == {"a": 1}


def test_parse_json_no_parseable_devuelve_unparsed():
    assert parse_json("esto no es json") == {"_unparsed": "esto no es json"}


# --- format_chunks ----------------------------------------------------------

def test_format_chunks_vacio_lo_indica():
    assert "No se recuperaron" in format_chunks([])


def test_format_chunks_incluye_id_y_texto():
    salida = format_chunks([_chunk("cc_2356")])
    assert "cc_2356" in salida and "texto de cc_2356" in salida


# --- pasos de razonamiento --------------------------------------------------

def test_frame_case_estructura():
    spy = SpyLLM('{"tipo_hecho": "transito", "partes": {}, "hechos": [], '
                 '"danos_reclamados": [], "pruebas_aportadas": []}')
    res = frame_case("Texto de la demanda...", llm_fn=spy)
    assert res["tipo_hecho"] == "transito"
    assert "demanda" in (spy.user or "").lower()


def test_causation_inyecta_contrato_y_fragmentos():
    spy = SpyLLM('{"elementos": [], "puntos_debiles_defensa": [], '
                 '"razonamiento": "r", "citas": ["[FUENTE: cc_2356]"]}')
    res = analyze_causation({"tipo_hecho": "transito"}, [_chunk("cc_2356")], llm_fn=spy)

    assert res["citas"] == ["[FUENTE: cc_2356]"]
    # El contrato de citas debe viajar en el system prompt (anti-alucinación).
    assert CITATION_CONTRACT in (spy.system or "")
    # El id recuperado debe llegar al prompt para que el modelo pueda citarlo.
    assert "cc_2356" in (spy.user or "")


def test_regime_usa_la_tabla_real_y_contrato():
    spy = SpyLLM('{"regimen": "objetiva", "normas": [], "matiz_doctrinal": "", '
                 '"razonamiento": "", "citas": []}')
    res = classify_regime({"tipo_hecho": "transito"}, config.REGIMEN_TABLE_PATH, llm_fn=spy)

    assert res["regimen"] == "objetiva"
    assert CITATION_CONTRACT in (spy.system or "")
    # La tabla de régimen debe incluirse en el prompt.
    assert "regimenes" in (spy.user or "")


@pytest.mark.parametrize(
    "func", [analyze_exoneration, analyze_damages, analyze_third_parties]
)
def test_pasos_con_retrieved_inyectan_contrato_y_fragmentos(func):
    """Los pasos que reciben fragmentos llevan el contrato al system y el id al user."""
    spy = SpyLLM('{"citas": ["[FUENTE: cc_2356]"]}')
    res = func({"tipo_hecho": "transito"}, [_chunk("cc_2356")], llm_fn=spy)

    assert "_unparsed" not in res                      # respuesta JSON parseada
    assert CITATION_CONTRACT in (spy.system or "")     # anti-alucinación en el prompt
    assert "cc_2356" in (spy.user or "")               # el fragmento llegó al modelo
