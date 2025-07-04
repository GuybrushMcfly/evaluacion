import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu

from modules.capacitacion_listados import mostrar_listado_general
from modules.capacitacion_analisis import mostrar_analisis
from modules.capacitacion_destacados import mostrar_destacados

def mostrar(supabase):
    st.markdown("<h1 style='font-size:26px;'>📊 Análisis y Gestión de Evaluaciones</h1>", unsafe_allow_html=True)

    # --- Carga inicial de datos
    evals = supabase.table("evaluaciones").select("*").execute().data or []
    agentes = supabase.table("agentes").select("cuil, apellido_nombre, activo, dependencia_general").execute().data or []
    unids = supabase.table("unidades_evaluacion").select("*").execute().data or []

    if not evals or not unids:
        st.warning("⚠️ No hay datos suficientes para mostrar esta vista.")
        return

    df_evals = pd.DataFrame(evals)

    seleccion = option_menu(
        menu_title=None,
        options=["📋 LISTADOS", "📊 ANÁLISIS", "🌟 DESTACADOS"],
        orientation="horizontal",
        default_index=0,
        styles={
            "container": {
                "padding": "0!important", 
                "background-color": "transparent",
            },
            "nav-link": {
                "font-size": "17px",
                "text-align": "center",
                "margin": "0 10px",
                "color": "white",
                "font-weight": "bold",
                "background-color": "#F05A7E",
                "border-radius": "8px",
                "--hover-color": "#b03a3f",
            },
            "nav-link-selected": {
                "background-color": "#5EABD6",
                "color": "#0C0909",
                "font-weight": "bold",
                "border-radius": "8px",
            },
        }
    )

    if seleccion == "📋 LISTADOS":
        mostrar_listado_general(df_evals, agentes)

    elif seleccion == "📊 ANÁLISIS":
        mostrar_analisis(df_evals, agentes, supabase)

    elif seleccion == "🌟 DESTACADOS":
        mostrar_destacados(df_evals, agentes)
