"""Recuperación RAG sobre el corpus cerrado (Paso 4).

Submódulos:
    corpus_loader   Lee y parsea las fuentes de `corpus/` (id, fuente, texto, url).
    ingest          Fragmenta, genera embeddings locales y persiste en ChromaDB.
    retriever       Dada una consulta, devuelve los top-k fragmentos con su `id`.

El corpus es cerrado: la recuperación solo puede devolver fragmentos cuyo `id`
existe en `corpus/`. Esto es la base de la Restricción dura #1 (cero alucinación).
"""
