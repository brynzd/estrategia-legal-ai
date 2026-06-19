"""Paso 1 — Extracción de texto del PDF de la demanda (PyMuPDF / fitz).

Convierte el PDF de la demanda en texto plano para alimentar el resto del
pipeline. No interpreta ni resume: solo extrae. `pdfplumber` se reserva para
tablas problemáticas y aún no se usa aquí.
"""

from __future__ import annotations

from pathlib import Path


def extract_text(pdf_path: str | Path) -> str:
    """Extrae el texto plano de un PDF de demanda.

    Args:
        pdf_path: Ruta al archivo PDF de la demanda.

    Returns:
        El texto concatenado de todas las páginas, separadas por salto de línea.

    Raises:
        FileNotFoundError: Si la ruta no existe.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el PDF: {path}")

    import fitz  # import perezoso: solo se necesita PyMuPDF al extraer

    doc = fitz.open(path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
