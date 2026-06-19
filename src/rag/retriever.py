"""Recuperación top-k sobre el índice del corpus (Fase 1).

Dada una consulta (régimen, issue jurídico, concepto de quantum, etc.), devuelve
los fragmentos más relevantes del corpus junto con su `id` de fuente, para que el
paso de razonamiento cite SOLO lo recuperado.

La función de embeddings se inyecta (`embed_fn`) para poder probar sin descargar
modelos; por defecto usa el mismo modelo que la ingesta.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import config
from .embeddings import EmbedFn, make_sentence_transformer_embedder
from .vector_store import NumpyVectorStore


@dataclass
class RetrievedChunk:
    """Fragmento recuperado del corpus.

    Attributes:
        id: `id` de la fuente del corpus (clave de la cita `[FUENTE: <id>]`).
        texto: Texto literal del fragmento.
        fuente: Nombre completo de la norma/sentencia.
        seccion: Artículo o sección.
        url: Enlace a la fuente oficial para verificación humana.
        score: Similitud de coseno (mayor = más relevante).
    """

    id: str
    texto: str
    fuente: str
    seccion: str
    url: str
    score: float


def retrieve(
    query: str,
    index_dir: Path | None = None,
    embed_fn: EmbedFn | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Recupera los `top_k` fragmentos más relevantes para una consulta.

    Args:
        query: Texto de la consulta (issue jurídico o concepto a documentar).
        index_dir: Carpeta del índice. Si es `None`, usa `config.INDEX_DIR`.
        embed_fn: Función de embeddings. Si es `None`, usa sentence-transformers
            con `config.EMBEDDING_MODEL` (debe coincidir con el de la ingesta).
        top_k: Número máximo de fragmentos. Si es `None`, usa `config.RETRIEVAL_TOP_K`.

    Returns:
        Lista de `RetrievedChunk` ordenada de más a menos relevante. Lista vacía
        si el índice no tiene fragmentos.
    """
    index_dir = Path(index_dir) if index_dir is not None else config.INDEX_DIR
    top_k = top_k if top_k is not None else config.RETRIEVAL_TOP_K
    if embed_fn is None:
        embed_fn = make_sentence_transformer_embedder(config.EMBEDDING_MODEL)

    store = NumpyVectorStore.load(index_dir)
    query_vec = embed_fn([query])[0]
    return [
        RetrievedChunk(
            id=chunk.source_id,
            texto=chunk.texto,
            fuente=chunk.fuente,
            seccion=chunk.seccion,
            url=chunk.url,
            score=score,
        )
        for chunk, score in store.search(query_vec, top_k)
    ]
