import streamlit as st
import pandas as pd

def cargar_agentes(supabase):
    datos = supabase.table("agentes").select("cuil, apellido_nombre, dependencia_general").execute().data
    return cachear_agentes(datos)

@st.cache_data(ttl=60)
def cachear_agentes(datos):
    return datos

def cargar_evaluaciones(supabase):
    datos = supabase.table("evaluaciones")\
        .select("cuil, anulada, anio_evaluacion, calificacion")\
        .eq("anio_evaluacion", 2024).execute().data
    return cachear_evaluaciones(datos)

@st.cache_data(ttl=60)
def cachear_evaluaciones(datos):
    return datos

def mostrar(supabase):
    st.header("📊 Estado General de Evaluación de Desempeño 2024")

    # Cargar agentes
    agentes = cargar_agentes(supabase)
    df_agentes = pd.DataFrame(agentes)

    # Cargar evaluaciones del año
    evaluaciones = cargar_evaluaciones(supabase)

    if evaluaciones:
        df_eval = pd.DataFrame(evaluaciones)
        if "anulada" in df_eval.columns:
            df_eval = df_eval[df_eval["anulada"] != True]
        df_eval = df_eval[df_eval["cuil"].notna()]
    else:
        df_eval = pd.DataFrame(columns=["cuil", "anulada", "anio_evaluacion", "calificacion"])

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

    # ---- CALIFICACIONES ----
    st.divider()
    st.subheader("🏅 Distribución por Calificación")

    categorias = ["DESTACADO", "BUENO", "REGULAR", "DEFICIENTE"]
    conteo = df_eval["calificacion"].value_counts().to_dict()
    col4, col5, col6, col7 = st.columns(4)
    col4.metric("🌟 Destacados", conteo.get("DESTACADO", 0))
    col5.metric("👍 Buenos", conteo.get("BUENO", 0))
    col6.metric("🟡 Regulares", conteo.get("REGULAR", 0))
    col7.metric("🔴 Deficientes", conteo.get("DEFICIENTE", 0))

    # ---- TABLA POR DEPENDENCIA GENERAL ----
    st.divider()
    st.subheader("🏢 Avance por Dependencia General")

    df_agentes["evaluado"] = df_agentes["cuil"].isin(df_eval["cuil"])

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
