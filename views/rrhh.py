import streamlit as st
import pandas as pd


def mostrar(supabase):
    st.markdown("## 🧮 Estado General de Evaluación de Desempeño 2025")

    # Cargar agentes
    agentes = supabase.table("agentes").select("cuil, apellido_nombre, dependencia_general").execute().data
    df_agentes = pd.DataFrame(agentes)

    # Cargar evaluaciones válidas

    evaluaciones = supabase.table("evaluaciones")\
        .select("cuil, anulada, anio_evaluacion")\
        .eq("anio_evaluacion", 2025).execute().data
    df_eval = pd.DataFrame(evaluaciones)
    
    if not df_eval.empty and "anulada" in df_eval.columns:
        df_eval = df_eval[df_eval["anulada"] != True]


    # Filtrar evaluaciones no anuladas
    df_eval = df_eval[df_eval["anulada"] != True]

    # ---- PROGRESO GENERAL ----
    total_agentes = len(df_agentes)
    evaluados = df_eval["cuil"].nunique()

    porcentaje = round((evaluados / total_agentes) * 100) if total_agentes > 0 else 0

    st.subheader("🔵 Progreso General")
    st.progress(porcentaje / 100)
    st.markdown(f"**{evaluados} de {total_agentes} personas evaluadas.** ({porcentaje}%)")

    # ---- TABLA POR DEPENDENCIA GENERAL ----
    st.subheader("📊 Avance por Dependencia General")

    # Unir agentes con evaluaciones
    df_agentes["evaluado"] = df_agentes["cuil"].isin(df_eval["cuil"])

    # Agrupar
    resumen = df_agentes.groupby("dependencia_general").agg(
        agentes_total=("cuil", "count"),
        evaluados=("evaluado", "sum")
    ).reset_index()

    resumen["% Evaluación"] = ((resumen["evaluados"] / resumen["agentes_total"]) * 100).round().astype(int)

    # Ordenar por % evaluación descendente
    resumen = resumen.sort_values("% Evaluación", ascending=False)

    # Mostrar tabla
    st.dataframe(resumen.rename(columns={
        "dependencia_general": "Dependencia General",
        "agentes_total": "Agentes a Evaluar",
        "evaluados": "Evaluados"
    }), use_container_width=True)

