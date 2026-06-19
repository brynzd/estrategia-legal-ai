"""Capa de embeddings (desacoplada del resto del RAG).

Aísla el modelo de embeddings detrás de una función `EmbedFn` (recibe una lista de
textos y devuelve una matriz numpy de vectores L2-normalizados). Así la ingesta y
la recuperación no dependen de un backend concreto y son testeables inyectando un
embedder simulado (sin descargar modelos).

Backend por defecto: `sentence-transformers` local (CLAUDE.md), parametrizable por
`config.EMBEDDING_MODEL`. Funciona en Python 3.14 (torch sí tiene wheel cp314).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Callable

import numpy as np

# Una EmbedFn convierte una lista de textos en una matriz (N, d) normalizada.
EmbedFn = Callable[[list[str]], np.ndarray]


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    """Carga (y cachea) un modelo de sentence-transformers.

    Args:
        model_name: Nombre del modelo (p. ej. `intfloat/multilingual-e5-large`).

    Returns:
        La instancia de `SentenceTransformer`.
    """
    from sentence_transformers import SentenceTransformer  # import perezoso

    return SentenceTransformer(model_name)


def make_sentence_transformer_embedder(model_name: str) -> EmbedFn:
    """Crea una `EmbedFn` respaldada por sentence-transformers.

    Args:
        model_name: Nombre del modelo de embeddings.

    Returns:
        Una función que embebe una lista de textos a una matriz numpy normalizada.
    """

    def embed(texts: list[str]) -> np.ndarray:
        model = _load_model(model_name)
        return model.encode(
            list(texts), normalize_embeddings=True, convert_to_numpy=True
        )

    return embed
