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
 #       icons=["bar-chart-line", "clipboard-check"],
        orientation="horizontal",
        default_index=0,
        
        styles={
            "container": {
                "padding": "0!important", 
                "background-color": "transparent",
                # "max-width": "800px",  # ← Eliminar esta línea
                # "margin": "0 auto"     # ← Eliminar esta línea
            },
            "nav-link": {
                "font-size": "17px",
                "text-align": "center",
                "margin": "0 10px",
               # "flex": "1",  # ← Esto hace que se distribuyan uniformemente
                "max-width": "280px",  # ← Eliminar esta línea
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
        st.subheader("📊 Análisis de Evaluaciones por Dependencia General")
    
        # Obtener datos desde Supabase
        evaluaciones_data = supabase.table("evaluaciones").select("*").execute().data
        df = pd.DataFrame(evaluaciones_data)
        df = df[df["anulada"] != True]  # Aplicar el mismo filtro que en LISTADOS
        
        if df.empty or "dependencia_general" not in df.columns:
            st.warning("No hay datos disponibles.")
            st.stop()
        
        # Asegurarse que formulario existe y convertir nivel
        df = df[df["formulario"].notnull()]  # eliminar filas sin formulario
        df["nivel"] = df["formulario"].astype(int)
        
        df["residual"] = False  # Inicializamos como no residual
    
        # Lista de direcciones únicas (SIN la opción "Todas")
        direcciones = sorted(df["dependencia_general"].dropna().unique())
        opciones = ["- Seleccionar Dirección -"] + direcciones + ["Unidad Residual"]
    
        seleccion_dir = st.selectbox("📍 Seleccione Dirección", opciones)
    
        if seleccion_dir != "- Seleccionar Dirección -":
            if st.button("🔍 Analizar"):
                if seleccion_dir == "Unidad Residual":
                    df_filtrada = df[df["nivel"] == 1].copy()
                    df_filtrada["residual"] = True
                else:
                    df_filtrada = df[df["dependencia_general"] == seleccion_dir].copy()
    
                st.write(f"👥 Evaluaciones encontradas: {len(df_filtrada)}")
    
                def mostrar_tabla(df_subset, titulo, niveles):
                    subset = df_subset[df_subset["nivel"].isin(niveles)].copy()
                    st.markdown(f"### 🔹 {titulo}")
                    if subset.empty:
                        st.info("No se calificaron con esos niveles.")
                    elif len(subset) < 6:
                        st.warning("Hubo menos de 6 calificaciones. Pasaron a Residual.")
                        df.loc[subset.index, "residual"] = True
                        # NO mostrar tabla si son residuales
                    else:
                        st.success("Grupo válido. No Residual.")
                        df.loc[subset.index, "residual"] = False
                        st.dataframe(subset[["apellido_nombre", "formulario", "calificacion", "puntaje_total"]].rename(columns={"puntaje_total": "puntaje"}))
    
                # Solo analizar si no es "Unidad Residual"
                if seleccion_dir != "Unidad Residual":
                    # Nivel Medio (2, 3, 4)
                    mostrar_tabla(df_filtrada, "Niveles Medios (2, 3, 4)", [2, 3, 4])
    
                    # Nivel Operativo (5, 6)
                    mostrar_tabla(df_filtrada, "Niveles Operativos (5, 6)", [5, 6])
    
                    # Nivel 1: siempre residual
                    df_nivel1 = df_filtrada[df_filtrada["nivel"] == 1].copy()
                    if not df_nivel1.empty:
                        df.loc[df_nivel1.index, "residual"] = True
    
                # Actualizar en Supabase solo los evaluados en esta dependencia
                cambios = df.loc[df_filtrada.index, ["id_evaluacion", "residual"]]
                for _, row in cambios.iterrows():
                    supabase.table("evaluaciones").update({
                        "residual": row["residual"]
                    }).eq("id_evaluacion", row["id_evaluacion"]).execute()
    
                st.success("✅ Evaluaciones analizadas y actualizadas correctamente.")

    # SIEMPRE mostrar tabla de residuales al final
    st.markdown("### 🔄 Tabla de Residuales")
    df_residuales = df[df["residual"] == True].copy()
    
    if df_residuales.empty:
        st.info("No hay evaluaciones marcadas como residuales.")
    else:
        # Agregar nombre del agente
        mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}
        df_residuales["agente"] = df_residuales["cuil"].map(mapa_agentes)
        
        st.dataframe(
            df_residuales[["agente", "dependencia_general", "formulario", "calificacion", "puntaje_total"]].rename(columns={
                "agente": "AGENTE",
                "dependencia_general": "DEPENDENCIA",
                "formulario": "FORMULARIO",
                "calificacion": "CALIFICACIÓN",
                "puntaje_total": "PUNTAJE"
            }),
            use_container_width=True,
            hide_index=True
        )

    elif seleccion == "🌟 DESTACADOS":
        st.markdown("### 🌟 Cupo DESTACADOS por Dependencia General")

        # --- Preparar dataframes
        df_agentes = pd.DataFrame(agentes)
     #   df_agentes = df_agentes[df_agentes["activo"] == True]

        df_eval_validas = df_evals[
            (df_evals["calificacion"] == "DESTACADO") & (df_evals["anulada"] != True)
        ]

        # --- Agrupar por dependencia
        # --- Agrupar por dependencia
        resumen = df_agentes.groupby("dependencia_general").agg(
            total_agentes=("cuil", "count")
        ).reset_index()
        resumen["cupo_destacados"] = resumen["total_agentes"].apply(lambda x: math.floor(x * 0.3) if (x * 0.3) - math.floor(x * 0.3) <= 0.5 else math.floor(x * 0.3) + 1)
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
        # --- Descargar Excel para DESTACADOS
        df_destacados_excel = resumen.copy()
        # Convertir emojis a texto para Excel
        def estado_texto(row):
            if row["evaluados_con_destacado"] == 0:
                return "SIN EVALUACIONES"
            elif row["evaluados_con_destacado"] <= row["cupo_destacados"]:
                return "DENTRO DEL CUPO"
            else:
                return "EXCEDE CUPO"
        
        df_destacados_excel["Estado_Excel"] = df_destacados_excel.apply(estado_texto, axis=1)
        df_destacados_excel = df_destacados_excel.drop("Estado", axis=1)
        df_destacados_excel = df_destacados_excel.rename(columns={"Estado_Excel": "ESTADO"})
        
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


