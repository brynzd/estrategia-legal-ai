"""Ingesta del corpus al índice vectorial (Fase 1).

Lee el corpus, fragmenta cada documento, genera embeddings locales y persiste el
índice. Cada fragmento conserva el `id` de su fuente como metadato, condición de la
trazabilidad de las citas.

La función de embeddings se inyecta (`embed_fn`) para poder probar la ingesta con
un embedder simulado, sin descargar modelos.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .. import config
from .corpus_loader import load_corpus
from .embeddings import EmbedFn, make_sentence_transformer_embedder
from .vector_store import NumpyVectorStore, StoredChunk


def chunk_text(texto: str, max_chars: int = 600, overlap: int = 80) -> list[str]:
    """Fragmenta un texto en trozos solapados por longitud de caracteres.

    Fragmentación simple (no se complica con análisis lingüístico): si el texto
    cabe en `max_chars` se devuelve entero; si no, se corta en ventanas con solape
    para no perder contexto en los bordes.

    Args:
        texto: Texto a fragmentar.
        max_chars: Tamaño máximo de cada fragmento en caracteres.
        overlap: Solape en caracteres entre fragmentos consecutivos.

    Returns:
        Lista de fragmentos no vacíos (lista vacía si el texto está vacío).
    """
    texto = texto.strip()
    if not texto:
        return []
    if len(texto) <= max_chars:
        return [texto]

    fragmentos: list[str] = []
    start = 0
    paso = max(1, max_chars - overlap)
    while start < len(texto):
        fragmento = texto[start : start + max_chars].strip()
        if fragmento:
            fragmentos.append(fragmento)
        start += paso
    return fragmentos


def build_index(
    corpus_dir: Path,
    index_dir: Path,
    embed_fn: EmbedFn | None = None,
    max_chars: int = 600,
) -> int:
    """Construye (o reconstruye) el índice vectorial del corpus.

    Args:
        corpus_dir: Carpeta raíz del corpus.
        index_dir: Carpeta donde se persiste el índice.
        embed_fn: Función de embeddings a usar. Si es `None`, usa
            sentence-transformers con `config.EMBEDDING_MODEL`.
        max_chars: Tamaño máximo de fragmento (caracteres).

    Returns:
        Número de fragmentos indexados.
    """
    if embed_fn is None:
        embed_fn = make_sentence_transformer_embedder(config.EMBEDDING_MODEL)

    docs = load_corpus(Path(corpus_dir))
    chunks: list[StoredChunk] = []
    textos: list[str] = []
    for doc in docs:
        for i, fragmento in enumerate(chunk_text(doc.texto, max_chars)):
            chunks.append(
                StoredChunk(
                    source_id=doc.id,
                    chunk_id=f"{doc.id}#{i}",
                    texto=fragmento,
                    fuente=doc.fuente,
                    seccion=doc.seccion,
                    url=doc.url,
                )
            )
            textos.append(fragmento)

    if not textos:
        NumpyVectorStore(np.zeros((0, 1), dtype=np.float32), []).save(Path(index_dir))
        return 0

    embeddings = np.asarray(embed_fn(textos))
    NumpyVectorStore(embeddings, chunks).save(Path(index_dir))
    return len(chunks)
