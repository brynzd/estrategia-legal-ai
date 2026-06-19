"""Configuración central del proyecto.

Centraliza rutas y parámetros (modelos, top-k, proveedor de LLM) leyendo de
variables de entorno con valores por defecto razonables. Las claves de API se
cargan desde `.env` (ver `.env.example`); nunca se hardcodean aquí.

Uso típico:
    from src import config
    print(config.CORPUS_DIR)
    provider = config.LLM_PROVIDER
"""

from __future__ import annotations

import os
from pathlib import Path

# Carga opcional de .env. Si python-dotenv no está instalado, se siguen usando
# las variables de entorno del sistema sin romper el import.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dependencia opcional en este punto
    pass


# --- Rutas del proyecto -----------------------------------------------------
# BASE_DIR es la raíz del repositorio (este archivo vive en src/).
BASE_DIR: Path = Path(__file__).resolve().parent.parent
CORPUS_DIR: Path = BASE_DIR / "corpus"
SAMPLES_DIR: Path = BASE_DIR / "samples"
OUTPUT_DIR: Path = BASE_DIR / "output"

REGIMEN_TABLE_PATH: Path = CORPUS_DIR / "regimen_table.yaml"
RUBRICA_SOLIDEZ_PATH: Path = CORPUS_DIR / "rubrica_solidez.md"


# --- LLM de razonamiento (parametrizable) -----------------------------------
# "anthropic" (Claude, por defecto) o "groq" (open, para el demo en vivo).
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic").lower()

ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")

GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# --- RAG / embeddings (locales, sin API) ------------------------------------
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
CHROMA_DIR: Path = Path(os.getenv("CHROMA_DIR", str(BASE_DIR / "data" / "chroma")))
# Directorio del índice vectorial local. El backend actual es numpy (búsqueda por
# coseno; ver src/rag/vector_store.py), elegido porque chroma-hnswlib no tiene wheel
# para Python 3.14. Intercambiable por ChromaDB si se baja a Python 3.12.
INDEX_DIR: Path = Path(os.getenv("INDEX_DIR", str(BASE_DIR / "data" / "index")))
RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))


# --- Formato de citas (Restricción dura #2) ---------------------------------
# Toda afirmación jurídica del memorando cita con este formato; el validador
# (src/memo/validator.py) parsea este patrón y verifica el id contra el corpus.
CITATION_PREFIX: str = "FUENTE"
NOT_FOUND_SENTINEL: str = "No encontrado en el corpus"
