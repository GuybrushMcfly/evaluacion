import streamlit as st
import pandas as pd
import io
import math
from datetime import datetime
from pytz import timezone
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from streamlit_option_menu import option_menu

from modules.capacitacion_utils import (
    generar_informe_comite_docx,
    generar_anexo_iii_docx,
    generar_cuadro_resumen_docx,
    analizar_evaluaciones_residuales
)

def mostrar(supabase):
    st.markdown("<h1 style='font-size:26px;'>📊 Análisis y Gestión de Evaluaciones</h1>", unsafe_allow_html=True)

    # --- Carga inicial de datos
    evals = supabase.table("evaluaciones").select("*").execute().data or []
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data or []
    unids = supabase.table("unidades_evaluacion").select("*").execute().data or []

    if not evals or not unids:
        st.warning("⚠️ No hay datos suficientes para mostrar esta vista.")
        return

    df_evals = pd.DataFrame(evals)
    df_unidades = pd.DataFrame(unids)
    opciones_dependencias = sorted(df_unidades["dependencia_general"].dropna().unique().tolist())
    opciones_dependencias.insert(0, "TODAS")

    dependencia_seleccionada = st.selectbox("📂 Seleccione una Dirección General", opciones_dependencias)

    if dependencia_seleccionada == "TODAS":
        df_filtrada = df_evals.copy()
    else:
        df_filtrada = df_evals[df_evals["dependencia_general"] == dependencia_seleccionada]

    # --- Menú de navegación (tabs estilo botones)
    seleccion = option_menu(
        menu_title=None,
        options=["📋 LISTADOS", "📊 ANÁLISIS", "🌟 DESTACADOS"],
        orientation="horizontal",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
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
        st.markdown("### 📑 Listado General de Evaluaciones")
        df_filtrada = df_filtrada[df_filtrada["anulada"] != True]
        df_agentes = pd.DataFrame(agentes)
        mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

        filas_tabla = []
        filas_excel = []

        for e in df_filtrada.to_dict(orient="records"):
            cuil = e.get("cuil", "")
            agente = mapa_agentes.get(cuil, "Desconocido")
            formulario = e.get("formulario", "")
            calificacion = e.get("calificacion", "")
            total = e.get("puntaje_total", "")
            fecha_eval = e.get("fecha_evaluacion")

            if fecha_eval:
                try:
                    fecha = pd.to_datetime(fecha_eval, utc=True).tz_convert(timezone("America/Argentina/Buenos_Aires"))
                    fecha_str = fecha.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    fecha_str = ""
            else:
                fecha_str = ""

            filas_tabla.append({
                "DEPENDENCIA GENERAL": e.get("dependencia_general", ""),
                "AGENTE": agente,
                "FORMULARIO": formulario,
                "CALIFICACIÓN": calificacion,
                "FECHA": fecha_str
            })

            resumen_puntaje = ", ".join([f"{k} ({v})" for k, v in e.get("factor_puntaje", {}).items()])
            resumen_posicion = ", ".join([f"{k} ({v})" for k, v in e.get("factor_posicion", {}).items()])

            filas_excel.append({
                "CUIL": cuil,
                "AGENTE": agente,
                "FORMULARIO": formulario,
                "FACTOR/PUNTAJE": resumen_puntaje,
                "FACTOR/POSICION": resumen_posicion,
                "CALIFICACIÓN": calificacion,
                "PUNTAJE TOTAL": total,
                "PUNTAJE MÁXIMO": e.get("puntaje_maximo", ""),
                "PUNTAJE RELATIVO": e.get("puntaje_relativo", ""),
                "DEPENDENCIA": e.get("dependencia", ""),
                "DEPENDENCIA GENERAL": e.get("dependencia_general", "")
            })

        df_tabla = pd.DataFrame(filas_tabla)
        st.dataframe(df_tabla.sort_values("FECHA", ascending=False), use_container_width=True)

        # Descargar Excel
        df_excel = pd.DataFrame(filas_excel).sort_values(["DEPENDENCIA GENERAL", "FORMULARIO", "AGENTE"])
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_excel.to_excel(writer, index=False, sheet_name="Resumen")
        st.download_button(
            label="📥 Descargar Listado General (Excel)",
            data=buffer.getvalue(),
            file_name="listado_general.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    elif seleccion == "📊 ANÁLISIS":
        st.info("🔧 Esta sección está en construcción.")

    elif seleccion == "🌟 DESTACADOS":
        st.info("🌟 Esta sección está en construcción.")
