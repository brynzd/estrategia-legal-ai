"""UI de EstrategIA Legal (Streamlit) — Fase 4.

Sube el PDF de una demanda, ejecuta el pipeline de razonamiento y muestra:
  - el memorando de estrategia defensiva (ordenado por solidez),
  - el panel de trazabilidad (cómo se llegó a cada conclusión: paso a paso),
  - la validación de citas (anti-alucinación) con enlace a la fuente oficial.

Ejecutar:  streamlit run app.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st

from src import config
from src.memo.builder import DISCLAIMER
from src.memo.validator import extract_citations
from src.pipeline import run_pipeline
from src.rag.corpus_loader import load_corpus

st.set_page_config(page_title="EstrategIA Legal", page_icon="⚖️", layout="wide")

# Etiquetas legibles para los pasos del pipeline (para que "se vea que razona").
_ETIQUETAS_BASE = {
    "extraccion": "1 · Extracción del PDF",
    "encuadre_caso": "2 · Encuadre del caso (hechos estructurados)",
    "clasificacion_regimen": "3 · Clasificación de régimen",
    "nexo_causal": "5 · Nexo causal",
    "exoneracion": "5 · Causales de exoneración",
    "perjuicio": "5 · Perjuicio",
    "terceros": "5 · Vinculación de terceros",
    "memo:orden_solidez": "6 · Memorando · orden por solidez",
    "memo:encuadre": "6 · Memorando · encuadre",
    "validacion_citas": "7 · Validación de citas",
}


@st.cache_data(show_spinner=False)
def cargar_fuentes(corpus_dir: str) -> dict[str, dict]:
    """Mapa id -> {fuente, url, seccion} del corpus, para enlazar cada cita.

    Args:
        corpus_dir: Ruta del corpus (string para que sea cacheable).

    Returns:
        Dict indexado por `id` de documento con su nombre de fuente, url y sección.
    """
    docs = load_corpus(Path(corpus_dir))
    return {d.id: {"fuente": d.fuente, "url": d.url, "seccion": d.seccion} for d in docs}


def _etiqueta_paso(name: str) -> str:
    """Convierte el nombre técnico de un paso en una etiqueta legible."""
    if name in _ETIQUETAS_BASE:
        return _ETIQUETAS_BASE[name]
    if name.startswith("recuperacion:"):
        return f"4 · Recuperación RAG · {name.split(':', 1)[1]}"
    if name.startswith("memo:"):
        return f"6 · Memorando · {name.split(':', 1)[1]}"
    return name


def render_fuentes(ids: list[str], fuentes: dict[str, dict]) -> None:
    """Muestra una lista de ids de cita con su fuente y enlace oficial.

    Args:
        ids: Ids de documento citados (claves del corpus).
        fuentes: Mapa de `cargar_fuentes`.
    """
    if not ids:
        st.caption("— sin citas —")
        return
    for cid in ids:
        info = fuentes.get(cid)
        if info and info.get("url"):
            etiqueta = info["fuente"] or cid
            if info.get("seccion"):
                etiqueta += f" ({info['seccion']})"
            st.markdown(f"- `{cid}` — [{etiqueta}]({info['url']})")
        elif info:
            st.markdown(f"- `{cid}` — {info['fuente'] or '(sin nombre)'}")
        else:
            st.markdown(f"- `{cid}` — ⚠️ **no existe en el corpus** (cita huérfana)")


def render_salida(output, fuentes: dict[str, dict]) -> None:
    """Renderiza la salida de un paso según su tipo (prosa, dict o lista de ids)."""
    if isinstance(output, str):
        st.markdown(output or "_(vacío)_")
    elif isinstance(output, dict):
        st.json(output)
        citas = output.get("citas")
        if citas:
            st.markdown("**Fuentes citadas en este paso:**")
            render_fuentes(extract_citations(" ".join(map(str, citas))), fuentes)
    elif isinstance(output, list) and all(isinstance(x, str) for x in output):
        # Lista de ids recuperados (paso de recuperación RAG).
        render_fuentes(output, fuentes)
    else:
        st.write(output)


# --- Estado del sistema (barra lateral) -------------------------------------

fuentes = cargar_fuentes(str(config.CORPUS_DIR))
index_ok = (config.INDEX_DIR / "embeddings.npy").exists()
api_ok = bool(config.GROQ_API_KEY) if config.LLM_PROVIDER == "groq" else bool(config.ANTHROPIC_API_KEY)

with st.sidebar:
    st.header("Estado del sistema")
    st.markdown(f"**LLM:** `{config.LLM_PROVIDER}`")
    st.markdown("**API key:** " + ("✅ presente" if api_ok else "❌ falta (revisa `.env`)"))
    st.markdown(f"**Fuentes en el corpus:** {len(fuentes)}")
    st.markdown("**Índice RAG:** " + ("✅ construido" if index_ok else "❌ no construido"))

    if st.button("🔄 Reconstruir índice del corpus"):
        try:
            from src.rag.ingest import build_index

            with st.spinner("Indexando corpus (puede descargar el modelo de embeddings)…"):
                n = build_index(config.CORPUS_DIR, config.INDEX_DIR)
            st.success(f"Índice construido: {n} fragmentos.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001 - feedback directo al usuario
            st.error(f"No se pudo construir el índice: {exc}")

    if len(fuentes) == 0:
        st.warning("El corpus está vacío. Los abogados deben cargar normas y "
                   "jurisprudencia en `corpus/` antes de obtener resultados útiles.")


# --- Cabecera ---------------------------------------------------------------

st.title("⚖️ EstrategIA Legal")
st.caption(
    "Apoyo a la decisión defensiva en Responsabilidad Civil Extracontractual (Colombia). "
    "Razonamiento jurídico trazable sobre un corpus cerrado y verificado."
)
st.info(DISCLAIMER, icon="ℹ️")

if "result" not in st.session_state:
    st.session_state.result = None

uploaded = st.file_uploader("Sube el PDF de la demanda", type=["pdf"])

# --- Ejecución del pipeline -------------------------------------------------

if uploaded is not None and st.button("Analizar demanda", type="primary"):
    if not index_ok:
        st.warning("No hay índice RAG. Constrúyelo desde la barra lateral antes de analizar.")
    elif not api_ok:
        st.warning("Falta la API key del LLM. Configúrala en `.env` (ver `.env.example`).")
    else:
        pdf_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded.getbuffer())
                pdf_path = Path(tmp.name)
            with st.spinner("Ejecutando el pipeline de razonamiento…"):
                st.session_state.result = run_pipeline(pdf_path)
        except Exception as exc:  # noqa: BLE001 - se muestra al usuario
            st.session_state.result = None
            st.error(f"No se pudo ejecutar el pipeline: {exc}")
            st.info("Revisa: (1) API key en `.env`, (2) índice construido (barra lateral), "
                    "(3) corpus con fuentes reales.")
        finally:
            if pdf_path and pdf_path.exists():
                os.unlink(pdf_path)


# --- Resultados -------------------------------------------------------------

result = st.session_state.result
if result is not None:
    report = result.citation_report

    # Banner de validación de citas (anti-alucinación) siempre visible.
    if report.is_valid:
        st.success(f"✅ Citas verificadas contra el corpus: {len(report.valid_ids)} válidas, 0 huérfanas.")
    else:
        st.error(f"❌ Citas huérfanas (no existen en el corpus): {', '.join(report.orphan_ids)}")

    memo_tab, traza_tab, citas_tab = st.tabs(
        ["📝 Memorando", "🔍 Panel de trazabilidad", "✅ Validación de citas"]
    )

    with memo_tab:
        st.markdown(result.memo)
        st.divider()
        st.subheader("Fuentes citadas en el memorando")
        st.caption("Cada cita enlaza a la fuente oficial para verificación humana.")
        render_fuentes(report.cited_ids, fuentes)

    with traza_tab:
        st.caption(
            "Flujo: Extracción → Encuadre → Recuperación RAG → Régimen → "
            "Nexo / Exoneración / Perjuicio / Terceros → Memorando → Validación. "
            "Cada paso registra su entrada y su salida."
        )
        for step in result.traces:
            with st.expander(f"{_etiqueta_paso(step.name)}  ·  {step.timestamp}"):
                st.markdown("**Entrada**")
                render_salida(step.input, fuentes)
                st.markdown("**Salida**")
                render_salida(step.output, fuentes)

    with citas_tab:
        st.subheader("Validación de citas (Restricción dura #2)")
        if report.is_valid:
            st.success("Todas las citas referencian un `id` existente en el corpus.")
        else:
            st.error("Hay citas que no existen en el corpus; el memorando no debe entregarse así.")
        st.markdown("**Citas válidas**")
        render_fuentes(report.valid_ids, fuentes)
        if report.orphan_ids:
            st.markdown("**Citas huérfanas (ERROR)**")
            render_fuentes(report.orphan_ids, fuentes)
else:
    st.caption("Sube un PDF y pulsa **Analizar demanda** para ver el memorando y su trazabilidad.")
