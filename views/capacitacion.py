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
    agentes = supabase.table("agentes").select("cuil, apellido_nombre, activo, dependencia_general").execute().data or []
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
        st.markdown("### 🌟 Cupo DESTACADOS por Dependencia General")

        # --- Preparar dataframes
        df_agentes = pd.DataFrame(agentes)
     #   df_agentes = df_agentes[df_agentes["activo"] == True]

        df_eval_validas = df_evals[
            (df_evals["calificacion"] == "DESTACADO") & (df_evals["anulada"] != True)
        ]

        # --- Agrupar por dependencia
        resumen = df_agentes.groupby("dependencia_general").agg(
            total_agentes=("cuil", "count")
        ).reset_index()
        resumen["cupo_destacados"] = resumen["total_agentes"].apply(lambda x: math.floor(x * 0.3))

        evaluados_destacados = df_eval_validas.groupby("dependencia_general").agg(
            evaluados_con_destacado=("cuil", "count")
        ).reset_index()

        resumen = pd.merge(resumen, evaluados_destacados, on="dependencia_general", how="left")
        resumen["evaluados_con_destacado"] = resumen["evaluados_con_destacado"].fillna(0).astype(int)

        # --- Estado visual
        def calcular_estado(row):
            if row["evaluados_con_destacado"] == 0:
                return "🟡"
            elif row["evaluados_con_destacado"] <= row["cupo_destacados"]:
                return "🟢"
            else:
                return "🔴"

        resumen["Estado"] = resumen.apply(calcular_estado, axis=1)

        # --- Mostrar tabla
        st.dataframe(
            resumen.rename(columns={
                "dependencia_general": "DEPENDENCIA GENERAL",
                "total_agentes": "AGENTES",
                "cupo_destacados": "CUPO (30%)",
                "evaluados_con_destacado": "EVALUADOS"
            }),
            use_container_width=True,
            hide_index=True
        )


        # --- Descargar Excel para DESTACADOS
        df_destacados_excel = resumen.copy()
        buffer_destacados = io.BytesIO()
        with pd.ExcelWriter(buffer_destacados, engine="xlsxwriter") as writer:
            df_destacados_excel.to_excel(writer, index=False, sheet_name="Destacados")
        st.download_button(
            label="📥 Descargar Cupo DESTACADOS (Excel)",
            data=buffer_destacados.getvalue(),
            file_name="cupo_destacados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # --- Métricas globales
        total_agentes = resumen["total_agentes"].sum()
        total_cupo = resumen["cupo_destacados"].sum()
        total_usados = resumen["evaluados_con_destacado"].sum()

        st.markdown("### 📊 Indicadores")
        col1, col2, col3 = st.columns(3)
        col1.metric("👥 Total de Agentes", total_agentes)
        col2.metric("🏅 Cupo total de DESTACADOS", total_cupo)
        col3.metric("✅ DESTACADOS Asignados", total_usados)


