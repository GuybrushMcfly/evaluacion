import streamlit as st
import pandas as pd
from pytz import timezone

def mostrar_indicadores(data):
    df_no_anuladas = data['df_no_anuladas']
    total_asignados = data['total_asignados']
    evaluados = data['evaluados']
    porcentaje = data['porcentaje']

    st.divider()
    st.markdown("<h2 style='font-size:20px;'>📊 Indicadores</h2>", unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]: st.metric("👥 Total a Evaluar", total_asignados)
    with cols[1]: st.metric("✅ Evaluados", evaluados)
    with cols[2]: st.metric("📊 % Evaluación", f"{int(porcentaje)}%")
    st.progress(min(100, int(porcentaje)), text=f"Progreso de evaluaciones registradas: {int(porcentaje)}%")

    st.markdown("---")

    st.markdown("<h2 style='font-size:20px;'>🏅 Distribución por Calificación</h2>", unsafe_allow_html=True)
    categorias = ["DESTACADO", "BUENO", "REGULAR", "DEFICIENTE"]
    calif_counts = {cat: 0 for cat in categorias}
    if not df_no_anuladas.empty and "calificacion" in df_no_anuladas.columns:
        temp_counts = df_no_anuladas["calificacion"].value_counts()
        for cat in categorias:
            calif_counts[cat] = temp_counts.get(cat, 0)

    col_cats = st.columns(len(categorias))
    emojis = ["🌟", "👍", "🟡", "🔴"]
    for i, cat in enumerate(categorias):
        col_cats[i].metric(f"{emojis[i]} {cat.title()}", calif_counts[cat])

    st.markdown("---")

    st.markdown("<h2 style='font-size:24px;'>🗂️ Distribución por Nivel de Evaluación</h2>", unsafe_allow_html=True)
    df_no_anuladas["formulario"] = df_no_anuladas["formulario"].astype(str)
    niveles_eval = {
        "🔵 Nivel Jerárquico": ["1"],
        "🟣 Niveles Medios": ["2", "3", "4"],
        "🟢 Niveles Operativos": ["5", "6"]
    }

    cols = st.columns(3)
    for i, (titulo, formularios) in enumerate(niveles_eval.items()):
        cantidad = df_no_anuladas["formulario"].isin(formularios).sum()
        cols[i].metric(titulo, cantidad)
