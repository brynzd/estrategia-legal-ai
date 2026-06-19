"""
UI
Ejecutar:  streamlit run app.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from src.memo.builder import DISCLAIMER
from src.pipeline import run_pipeline

st.set_page_config(page_title="EstrategIA Legal", page_icon="⚖️", layout="wide")

st.title("EstrategIA Legal")
st.caption(
    "Apoyo a la decisión defensiva en Responsabilidad Civil Extracontractual (Colombia). "
    "Razonamiento jurídico trazable sobre un corpus cerrado y verificado."
)
st.info(DISCLAIMER, icon="ℹ️")

uploaded = st.file_uploader("Sube el PDF de la demanda", type=["pdf"])

if uploaded is not None and st.button("Analizar demanda", type="primary"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded.getbuffer())
        pdf_path = Path(tmp.name)

    try:
        with st.spinner("Ejecutando el pipeline de razonamiento…"):
            result = run_pipeline(pdf_path)
    except NotImplementedError as exc:
        st.warning(f"Pipeline aún en construcción: {exc}")
        st.stop()

    memo_tab, citas_tab, traza_tab = st.tabs(
        ["📝 Memorando", "✅ Validación de citas", "🔍 Panel de trazabilidad"]
    )

    with memo_tab:
        st.markdown(result.memo)

    with citas_tab:
        report = result.citation_report
        if report.is_valid:
            st.success(f"Todas las citas son válidas ({len(report.valid_ids)} verificadas).")
        else:
            st.error(f"Citas huérfanas (no existen en el corpus): {report.orphan_ids}")

    with traza_tab:
        st.caption("Entrada y salida de cada paso del pipeline.")
        for step in result.traces:
            with st.expander(f"Paso: {step.name}  ·  {step.timestamp}"):
                st.write("**Entrada**", step.input)
                st.write("**Salida**", step.output)
