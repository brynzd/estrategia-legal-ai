"""Tests del validador de citas
Prueba de forma aislada la anti-alucinación: parseo de citas, carga de
ids del corpus y detección de citas huérfanas.
"""

from __future__ import annotations

from src.memo.validator import (
    extract_citations,
    load_corpus_ids,
    validate_citations,
)


def test_extract_citations_orden_y_sin_duplicados():
    texto = (
        "El daño se rige por [FUENTE: cc_2356]. Reiterado en [FUENTE: csj_sc4407_2023] "
        "y de nuevo en [FUENTE: cc_2356]."
    )
    assert extract_citations(texto) == ["cc_2356", "csj_sc4407_2023"]


def test_extract_citations_tolera_espacios():
    assert extract_citations("[FUENTE:  ley769_art1  ]") == ["ley769_art1"]


def test_validate_citations_detecta_huerfanas():
    texto = "Válida [FUENTE: cc_2356]; inventada [FUENTE: cc_9999]."
    report = validate_citations(texto, valid_ids={"cc_2356"})

    assert not report.is_valid
    assert report.valid_ids == ["cc_2356"]
    assert report.orphan_ids == ["cc_9999"]


def test_validate_citations_todas_validas():
    report = validate_citations("[FUENTE: cc_2356]", valid_ids={"cc_2356"})
    assert report.is_valid
    assert report.orphan_ids == []


def test_load_corpus_ids_lee_md_y_json(tmp_path):
    (tmp_path / "normas").mkdir()
    (tmp_path / "normas" / "cc_2356.md").write_text(
        "---\nid: cc_2356\nfuente: Código Civil art. 2356\n---\nTexto literal.",
        encoding="utf-8",
    )
    (tmp_path / "jurisprudencia").mkdir()
    (tmp_path / "jurisprudencia" / "csj.json").write_text(
        '{"id": "csj_sc4407_2023", "fuente": "CSJ SC4407-2023", "texto": "..."}',
        encoding="utf-8",
    )

    ids = load_corpus_ids(tmp_path)
    assert ids == {"cc_2356", "csj_sc4407_2023"}
