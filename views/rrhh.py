import streamlit as st
import pandas as pd

def mostrar(supabase):
    st.header("📊 Estado General de Evaluación de Desempeño 2024")

    # Cargar agentes
    agentes = supabase.table("agentes").select("cuil, apellido_nombre, dependencia_general").execute().data
    df_agentes = pd.DataFrame(agentes)

    # Cargar evaluaciones del año
    evaluaciones = supabase.table("evaluaciones")\
        .select("cuil, anulada, anio_evaluacion")\
        .eq("anio_evaluacion", 2024).execute().data

    # Procesar evaluaciones si hay
    if evaluaciones:
        df_eval = pd.DataFrame(evaluaciones)
        if "anulada" in df_eval.columns:
            df_eval = df_eval[df_eval["anulada"] != True]
        df_eval = df_eval[df_eval["cuil"].notna()]
    else:
        df_eval = pd.DataFrame(columns=["cuil", "anulada", "anio_evaluacion"])

    # ---- INDICADORES ----
    st.divider()
    st.subheader("📈 Indicadores generales")

    total_agentes = len(df_agentes)
    evaluados = df_eval["cuil"].nunique()
    porcentaje = round((evaluados / total_agentes) * 100) if total_agentes > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Total a Evaluar", total_agentes)
    col2.metric("✅ Evaluados", evaluados)
    col3.metric("📊 % Evaluación", f"{porcentaje}%")

    st.progress(porcentaje / 100, text=f"Progreso de evaluaciones registradas: {porcentaje}%")

    # ---- TABLA POR DEPENDENCIA GENERAL ----
    st.divider()
    st.subheader("🏢 Avance por Dependencia General")

    # Marcar evaluados en agentes
    df_agentes["evaluado"] = df_agentes["cuil"].isin(df_eval["cuil"])

    # Agrupar por dependencia_general
    resumen = df_agentes.groupby("dependencia_general").agg(
        agentes_total=("cuil", "count"),
        evaluados=("evaluado", "sum")
    ).reset_index()

    resumen["% Evaluación"] = ((resumen["evaluados"] / resumen["agentes_total"]) * 100).round().astype(int)
    resumen = resumen.sort_values("% Evaluación", ascending=False)

    st.dataframe(
        resumen.rename(columns={
            "dependencia_general": "Dependencia General",
            "agentes_total": "Agentes a Evaluar",
            "evaluados": "Evaluados"
        }),
        use_container_width=True,
        hide_index=True
    )
