"""Vector store local persistente (backend numpy).

Almacén mínimo para un corpus pequeño (CLAUDE.md: "el corpus es pequeño; no hace
falta más"): guarda la matriz de embeddings y los metadatos de cada fragmento, y
busca por similitud de coseno. Como los embeddings se guardan normalizados, el
coseno es un simple producto punto.

Se eligió numpy en lugar de ChromaDB porque `chroma-hnswlib` no tiene wheel para
Python 3.14. La interfaz es deliberadamente pequeña para poder sustituir el backend
por ChromaDB si se baja a Python 3.12, sin tocar ingest.py ni retriever.py.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

_EMBEDDINGS_FILE = "embeddings.npy"
_CHUNKS_FILE = "chunks.json"


@dataclass
class StoredChunk:
    """Un fragmento indexado con su procedencia (para trazabilidad de citas).

    Attributes:
        source_id: `id` de la fuente del corpus (clave de la cita `[FUENTE: <id>]`).
        chunk_id: Identificador único del fragmento (`<source_id>#<n>`).
        texto: Texto del fragmento.
        fuente: Nombre completo de la norma/sentencia.
        seccion: Artículo o sección.
        url: Enlace a la fuente oficial.
    """

    source_id: str
    chunk_id: str
    texto: str
    fuente: str
    seccion: str
    url: str


class NumpyVectorStore:
    """Índice vectorial en memoria con persistencia en disco."""

    def __init__(self, embeddings: np.ndarray, chunks: list[StoredChunk]) -> None:
        """Crea el store.

        Args:
            embeddings: Matriz (N, d) de vectores normalizados, alineada con `chunks`.
            chunks: Lista de `StoredChunk`, uno por fila de `embeddings`.
        """
        self.embeddings = embeddings
        self.chunks = chunks

    def save(self, index_dir: Path) -> None:
        """Persiste el índice en `index_dir` (embeddings.npy + chunks.json).

        Args:
            index_dir: Carpeta destino (se crea si no existe).
        """
        index_dir = Path(index_dir)
        index_dir.mkdir(parents=True, exist_ok=True)
        np.save(index_dir / _EMBEDDINGS_FILE, self.embeddings)
        (index_dir / _CHUNKS_FILE).write_text(
            json.dumps([asdict(c) for c in self.chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, index_dir: Path) -> "NumpyVectorStore":
        """Carga un índice persistido.

        Args:
            index_dir: Carpeta donde se guardó el índice.

        Returns:
            El `NumpyVectorStore` reconstruido.

        Raises:
            FileNotFoundError: Si el índice no existe (hay que correr la ingesta).
        """
        index_dir = Path(index_dir)
        emb_path = index_dir / _EMBEDDINGS_FILE
        if not emb_path.exists():
            raise FileNotFoundError(
                f"No hay índice en {index_dir}. Ejecuta la ingesta (build_index) primero."
            )
        embeddings = np.load(emb_path)
        data = json.loads((index_dir / _CHUNKS_FILE).read_text(encoding="utf-8"))
        return cls(embeddings, [StoredChunk(**d) for d in data])

    def search(self, query_vec: np.ndarray, top_k: int = 5) -> list[tuple[StoredChunk, float]]:
        """Devuelve los `top_k` fragmentos más similares a `query_vec`.

        Args:
            query_vec: Vector de la consulta, normalizado (dimensión d).
            top_k: Número máximo de resultados.

        Returns:
            Lista de `(StoredChunk, score)` ordenada de mayor a menor similitud.
            Lista vacía si el índice no tiene fragmentos.
        """
        if len(self.chunks) == 0:
            return []
        scores = self.embeddings @ query_vec
        k = min(top_k, len(scores))
        top_idx = np.argsort(-scores)[:k]
        return [(self.chunks[i], float(scores[i])) for i in top_idx]
