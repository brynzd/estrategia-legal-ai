"""Validación de citas (Restricción dura #2 — anti-alucinación).

Tras generar el memorando, este paso parsea todas las citas con formato
`[FUENTE: <id>]` y comprueba que cada `<id>` exista realmente en el corpus.
Cualquier cita huérfana (id que no está en el corpus) se marca como ERROR y se
reporta; el memorando NO se entrega silenciosamente con citas inventadas.

Es lógica pura (sin LLM): parsing + pertenencia a un conjunto. Está pensada para
probarse de forma aislada (ver tests/test_validator.py).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# Captura el id dentro de [FUENTE: <id>] tolerando espacios alrededor del id.
_CITATION_RE = re.compile(r"\[FUENTE:\s*([^\]]+?)\s*\]")

# Captura `id: <valor>` en el front-matter de un archivo markdown del corpus.
_FRONTMATTER_ID_RE = re.compile(r"^id:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", re.MULTILINE)


@dataclass
class CitationReport:
    """Resultado de validar las citas de un texto contra el corpus.

    Attributes:
        cited_ids: Ids citados en el texto, en orden de aparición y sin duplicados.
        valid_ids: Ids citados que SÍ existen en el corpus.
        orphan_ids: Ids citados que NO existen en el corpus (errores a reportar).
    """

    cited_ids: list[str]
    valid_ids: list[str]
    orphan_ids: list[str]

    @property
    def is_valid(self) -> bool:
        """True si no hay ninguna cita huérfana."""
        return not self.orphan_ids


def extract_citations(text: str) -> list[str]:
    """Extrae los ids citados con formato `[FUENTE: <id>]`.

    Args:
        text: Texto del memorando (o de cualquier paso) que puede contener citas.

    Returns:
        Lista de ids en orden de aparición, sin duplicados.
    """
    seen: set[str] = set()
    ids: list[str] = []
    for match in _CITATION_RE.finditer(text):
        cid = match.group(1).strip()
        if cid and cid not in seen:
            seen.add(cid)
            ids.append(cid)
    return ids


def load_corpus_ids(corpus_dir: Path) -> set[str]:
    """Carga el conjunto de ids de documento presentes en el corpus.

    Recorre `corpus_dir` recursivamente y recoge el campo `id` de cada fuente,
    tanto en archivos `.json` como en el front-matter de archivos `.md`.

    Args:
        corpus_dir: Carpeta raíz del corpus (normalmente `config.CORPUS_DIR`).

    Returns:
        Conjunto de ids únicos encontrados en el corpus.
    """
    ids: set[str] = set()
    if not corpus_dir.exists():
        return ids

    for path in corpus_dir.rglob("*"):
        # Convención: los archivos que empiezan con "_" son plantillas/parciales,
        # no fuentes reales del corpus, y no aportan ids.
        if path.name.startswith("_"):
            continue
        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            records = data if isinstance(data, list) else [data]
            for rec in records:
                if isinstance(rec, dict) and rec.get("id"):
                    ids.add(str(rec["id"]).strip())
        elif path.suffix in {".md", ".markdown"}:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            match = _FRONTMATTER_ID_RE.search(text)
            if match:
                ids.add(match.group(1).strip())

    return ids


def validate_citations(text: str, valid_ids: set[str]) -> CitationReport:
    """Valida que toda cita del texto referencie un id existente en el corpus.

    Args:
        text: Texto del memorando a validar.
        valid_ids: Conjunto de ids válidos del corpus (ver `load_corpus_ids`).

    Returns:
        Un `CitationReport` con los ids citados, los válidos y los huérfanos.
    """
    cited = extract_citations(text)
    valid = [cid for cid in cited if cid in valid_ids]
    orphans = [cid for cid in cited if cid not in valid_ids]
    return CitationReport(cited_ids=cited, valid_ids=valid, orphan_ids=orphans)
