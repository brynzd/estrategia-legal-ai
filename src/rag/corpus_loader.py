"""Lectura y parseo del corpus jurídico (`corpus/`).

Carga cada fuente (JSON o markdown con front-matter) a una estructura uniforme
(`CorpusDoc`) que el resto del pipeline consume. Los campos provienen del formato
definido en CLAUDE.md: id, fuente, articulo/seccion, texto, url.

Convención: los archivos cuyo nombre empieza con `_` (p. ej. `_plantilla.md`) se
tratan como plantillas y se ignoran. Un documento sin `id` se omite (no es
trazable) y se registra en el log.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger("estrategia_legal")


@dataclass
class CorpusDoc:
    """Una fuente del corpus en forma uniforme.

    Attributes:
        id: Identificador único y estable (clave de trazabilidad de las citas).
        fuente: Nombre completo de la norma/sentencia.
        seccion: Artículo o sección (acepta el alias `articulo` en el origen).
        texto: Texto literal verificado.
        url: Enlace a la fuente oficial para verificación humana.
        path: Ruta del archivo de origen (traza de procedencia).
    """

    id: str
    fuente: str
    seccion: str
    texto: str
    url: str
    path: str


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Separa el front-matter YAML del cuerpo de un markdown.

    Args:
        text: Contenido del archivo markdown.

    Returns:
        Tupla `(metadatos, cuerpo)`. Si no hay front-matter, `metadatos` es `{}`
        y `cuerpo` es el texto completo.
    """
    if text.startswith("---"):
        partes = text.split("---", 2)
        if len(partes) == 3:
            meta = yaml.safe_load(partes[1]) or {}
            return (meta if isinstance(meta, dict) else {}), partes[2].strip()
    return {}, text.strip()


def _to_doc(meta: dict, texto: str, path: Path) -> CorpusDoc | None:
    """Construye un `CorpusDoc` a partir de metadatos + texto, o None si no es válido.

    Args:
        meta: Metadatos de la fuente (id, fuente, seccion/articulo, url).
        texto: Texto literal de la fuente.
        path: Ruta del archivo de origen.

    Returns:
        El `CorpusDoc` o `None` si falta el `id` (documento no trazable).
    """
    doc_id = str(meta.get("id", "")).strip()
    if not doc_id:
        logger.warning("Documento sin 'id' omitido: %s", path)
        return None
    return CorpusDoc(
        id=doc_id,
        fuente=str(meta.get("fuente", "")).strip(),
        seccion=str(meta.get("seccion", meta.get("articulo", ""))).strip(),
        texto=texto.strip(),
        url=str(meta.get("url", "")).strip(),
        path=str(path),
    )


def load_corpus(corpus_dir: Path) -> list[CorpusDoc]:
    """Carga todas las fuentes del corpus a una lista de `CorpusDoc`.

    Recorre `corpus_dir` recursivamente. Soporta markdown con front-matter
    (`.md`) y JSON (`.json`, objeto único o lista de objetos). Ignora archivos
    que empiezan con `_` (plantillas).

    Args:
        corpus_dir: Carpeta raíz del corpus (normalmente `config.CORPUS_DIR`).

    Returns:
        Lista de `CorpusDoc` con `id` válido, ordenada por `id`.
    """
    docs: list[CorpusDoc] = []
    if not corpus_dir.exists():
        logger.warning("El corpus no existe: %s", corpus_dir)
        return docs

    for path in sorted(corpus_dir.rglob("*")):
        if path.is_dir() or path.name.startswith("_"):
            continue

        if path.suffix in {".md", ".markdown"}:
            meta, cuerpo = _split_frontmatter(path.read_text(encoding="utf-8"))
            doc = _to_doc(meta, cuerpo, path)
            if doc:
                docs.append(doc)

        elif path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            registros = data if isinstance(data, list) else [data]
            for rec in registros:
                if not isinstance(rec, dict):
                    continue
                doc = _to_doc(rec, str(rec.get("texto", "")), path)
                if doc:
                    docs.append(doc)

    docs.sort(key=lambda d: d.id)
    logger.info("Corpus cargado: %d documentos desde %s", len(docs), corpus_dir)
    return docs
