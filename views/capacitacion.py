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
        
            # BOTÓN PRINCIPAL: Analizar todas las dependencias primero
            if st.button("🔍 Analizar Todas las Dependencias", type="primary"):
                
                # Obtener todas las dependencias únicas
                dependencias = df["dependencia_general"].dropna().unique()
                
                st.write(f"🏢 Analizando {len(dependencias)} dependencias...")
                
                # Analizar cada dependencia
                for dep in dependencias:
                    df_dep = df[df["dependencia_general"] == dep].copy()
                    
                    # Nivel 1: siempre residual
                    df_nivel1 = df_dep[df_dep["nivel"] == 1]
                    if not df_nivel1.empty:
                        df.loc[df_nivel1.index, "residual"] = True
                    
                    # Niveles Medios (2, 3, 4)
                    df_medios = df_dep[df_dep["nivel"].isin([2, 3, 4])]
                    if not df_medios.empty and len(df_medios) < 6:
                        df.loc[df_medios.index, "residual"] = True
                    
                    # Niveles Operativos (5, 6)
                    df_operativos = df_dep[df_dep["nivel"].isin([5, 6])]
                    if not df_operativos.empty and len(df_operativos) < 6:
                        df.loc[df_operativos.index, "residual"] = True
                
                # Actualizar en Supabase TODOS los cambios de residual
                cambios = df[["id_evaluacion", "residual"]]
                for _, row in cambios.iterrows():
                    supabase.table("evaluaciones").update({
                        "residual": row["residual"]
                    }).eq("id_evaluacion", row["id_evaluacion"]).execute()
                
                # Resetear bonificaciones solo para las dependencias analizadas
                for dep in dependencias:
                    supabase.table("evaluaciones").update({
                        "bonificacion_elegible": False
                    }).eq("dependencia_general", dep).execute()
                
                # Analizar BDD para cada dependencia
                for dep in dependencias:
                    df_dep = df[df["dependencia_general"] == dep].copy()
                    
                    # Filtrar elegibles según manual BDD
                    df_elegibles = df_dep[
                        (df_dep["calificacion"] == "DESTACADO") &  # Solo calificación Destacado
                        (df_dep["residual"] == False) &  # Excluir residuales
                        (df_dep["anulada"] != True)  # Excluir anuladas
                    ].copy()
                    
                    if not df_elegibles.empty:
                        # Calcular cupo de bonificaciones (10% del total evaluado)
                        total_evaluados = len(df_dep[df_dep["anulada"] != True])
                        cupo_bonificaciones = max(1, int(total_evaluados * 0.1))
                        
                        # Ordenar por puntaje relativo descendente
                        df_elegibles = df_elegibles.sort_values("puntaje_relativo", ascending=False)
                        
                        # Marcar quiénes reciben bonificación
                        elegibles_ids = df_elegibles.iloc[:cupo_bonificaciones]["id_evaluacion"].tolist()
                        
                        # Actualizar en base de datos
                        for id_eval in elegibles_ids:
                            supabase.table("evaluaciones").update({
                                "bonificacion_elegible": True
                            }).eq("id_evaluacion", id_eval).execute()
                
                # Analizar BDD para Unidad Residual
                df_residuales_bdd = df[
                    (df["residual"] == True) &  # Solo residuales
                    (df["calificacion"] == "DESTACADO") &  # Solo calificación Destacado
                    (df["anulada"] != True)  # Excluir anuladas
                ].copy()
                
                if not df_residuales_bdd.empty:
                    # Calcular cupo según regla residual: una bonificación por cada fracción superior a 5
                    total_residuales = len(df_residuales_bdd)
                    cupo_residual = max(1, total_residuales // 5)
                    
                    # Ordenar por puntaje relativo descendente
                    df_residuales_bdd = df_residuales_bdd.sort_values("puntaje_relativo", ascending=False)
                    
                    # Marcar quiénes reciben bonificación residual
                    residuales_ids = df_residuales_bdd.iloc[:cupo_residual]["id_evaluacion"].tolist()
                    
                    # Actualizar en base de datos
                    for id_eval in residuales_ids:
                        supabase.table("evaluaciones").update({
                            "bonificacion_elegible": True
                        }).eq("id_evaluacion", id_eval).execute()
                
                st.success("✅ Análisis completo realizado: Residuales y BDD procesados en todas las dependencias.")
                
                # Marcar que el análisis fue realizado usando session_state
                st.session_state.analisis_realizado = True
        
            # Mostrar contenido solo si se realizó el análisis
            if st.session_state.get("analisis_realizado", False):
                # Actualizar df con los datos más recientes de Supabase después del análisis
                evaluaciones_data_actualizada = supabase.table("evaluaciones").select("*").execute().data
                df = pd.DataFrame(evaluaciones_data_actualizada)
                df = df[df["anulada"] != True]
                df = df[df["formulario"].notnull()]
                df["nivel"] = df["formulario"].astype(int)
                
                st.markdown("---")
                st.markdown("### 📋 Ver Detalles por Dependencia")
                
                # Lista de direcciones únicas
                direcciones = sorted(df["dependencia_general"].dropna().unique())
                opciones = ["- Seleccionar Dirección -"] + direcciones
        
                seleccion_dir = st.selectbox("📍 Seleccione Dirección para ver detalles", opciones)
        
                if seleccion_dir != "- Seleccionar Dirección -":
                    df_filtrada = df[df["dependencia_general"] == seleccion_dir].copy()
                    st.write(f"👥 Evaluaciones encontradas en {seleccion_dir}: {len(df_filtrada)}")
        
                    def mostrar_detalle_tabla(df_subset, titulo, niveles):
                        subset = df_subset[df_subset["nivel"].isin(niveles)].copy()
                        st.markdown(f"### 🔹 {titulo}")
                        if subset.empty:
                            st.info("No se calificaron con esos niveles.")
                        elif len(subset) < 6:
                            st.warning(f"Hubo {len(subset)} calificaciones (menos de 6). Pasaron a Residual.")
                        else:
                            st.success(f"Grupo válido con {len(subset)} evaluaciones. No Residual.")
                            st.dataframe(subset[["apellido_nombre", "formulario", "calificacion", "puntaje_total"]].rename(columns={"puntaje_total": "puntaje"}))
        
                    # Mostrar detalles de cada nivel
                    mostrar_detalle_tabla(df_filtrada, "Niveles Medios (2, 3, 4)", [2, 3, 4])
                    mostrar_detalle_tabla(df_filtrada, "Niveles Operativos (5, 6)", [5, 6])
                    
                    # Mostrar Nivel 1 si existe
                    df_nivel1 = df_filtrada[df_filtrada["nivel"] == 1]
                    if not df_nivel1.empty:
                        st.markdown("### 🔹 Nivel 1 (Siempre Residual)")
                        st.info("Todas las evaluaciones de Nivel 1 van automáticamente a Residual.")
                    
                    # SECCIÓN BDD - Agregar después de mostrar Niveles y antes de Residuales
                    st.markdown("---")
                    st.markdown("### 🏆 Elegibles para Bonificación por Desempeño Destacado (10%)")
                    
                    # Filtrar elegibles según manual BDD
                    df_elegibles = df_filtrada[
                        (df_filtrada["calificacion"] == "DESTACADO") &  # Solo calificación Destacado
                        (df_filtrada["residual"] == False) &  # Excluir residuales
                        (df_filtrada["anulada"] != True)  # Excluir anuladas
                    ].copy()
                    
                    if df_elegibles.empty:
                        st.info("No hay personal elegible para BDD en esta dependencia.")
                    else:
                        # Calcular cupo de bonificaciones (10% del total evaluado)
                        total_evaluados = len(df_filtrada[df_filtrada["anulada"] != True])
                        cupo_bonificaciones = max(1, int(total_evaluados * 0.1))
                        
                        # Ordenar por puntaje relativo descendente (mayor puntaje primero)
                        df_elegibles = df_elegibles.sort_values("puntaje_relativo", ascending=False)
                        
                        # Determinar quiénes reciben efectivamente la bonificación
                        df_elegibles["recibe_bdd"] = df_elegibles["bonificacion_elegible"]
                        
                        # Mostrar métricas
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📊 Total Evaluados", total_evaluados)
                        with col2:
                            st.metric("🎯 Cupo BDD (10%)", cupo_bonificaciones)
                        with col3:
                            st.metric("⭐ Elegibles Destacado", len(df_elegibles))
                        
                        # Tabla de elegibles
                        st.dataframe(
                            df_elegibles[[
                                "apellido_nombre", 
                                "formulario", 
                                "calificacion", 
                                "puntaje_total",
                                "puntaje_relativo", 
                                "recibe_bdd"
                            ]].rename(columns={
                                "apellido_nombre": "AGENTE",
                                "formulario": "NIVEL",
                                "calificacion": "CALIFICACIÓN",
                                "puntaje_total": "PUNTAJE TOTAL",
                                "puntaje_relativo": "PUNTAJE RELATIVO",
                                "recibe_bdd": "RECIBE BDD"
                            }),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Mostrar advertencias si hay empates
                        if len(df_elegibles) > cupo_bonificaciones:
                            # Verificar si hay empates en el límite
                            puntaje_corte = df_elegibles.iloc[cupo_bonificaciones-1]["puntaje_relativo"]
                            empates = df_elegibles[df_elegibles["puntaje_relativo"] == puntaje_corte]
                            
                            if len(empates) > 1:
                                st.warning(f"⚠️ Hay {len(empates)} agentes empatados con puntaje {puntaje_corte:.3f}. Según manual BDD, el superior debe desempatar.")
                                st.dataframe(empates[["apellido_nombre", "puntaje_relativo"]])
        
                # SIEMPRE mostrar tabla de residuales al final
                st.markdown("---")
                st.markdown("### 🔄 Tabla Global de Residuales")
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
                    
                    st.metric("🔄 Total de Evaluaciones Residuales", len(df_residuales))
                    
                    # BDD para Unidad Residual
                    st.markdown("---")
                    st.markdown("### 🏆 Bonificaciones BDD - Unidad Residual")
                    
                    df_residuales_bdd = df_residuales[
                        (df_residuales["calificacion"] == "DESTACADO") &
                        (df_residuales["anulada"] != True)
                    ].copy()
                    
                    if df_residuales_bdd.empty:
                        st.info("No hay personal residual elegible para BDD (sin calificación DESTACADO).")
                    else:
                        # Calcular cupo según regla residual
                        total_residuales_destacado = len(df_residuales_bdd)
                        cupo_residual = max(1, total_residuales_destacado // 5)
                        
                        # Ordenar por puntaje relativo descendente
                        df_residuales_bdd = df_residuales_bdd.sort_values("puntaje_relativo", ascending=False)
                        
                        # Determinar quiénes reciben bonificación
                        df_residuales_bdd["recibe_bdd"] = df_residuales_bdd["bonificacion_elegible"]
                        
                        # Mostrar métricas
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📊 Residuales DESTACADO", total_residuales_destacado)
                        with col2:
                            st.metric("🎯 Cupo Residual (1 cada 5)", cupo_residual)
                        with col3:
                            porcentaje_residual = (cupo_residual / total_residuales_destacado) * 100 if total_residuales_destacado > 0 else 0
                            st.metric("📈 % Bonificados", f"{porcentaje_residual:.1f}%")
                        
                        # Tabla de BDD residuales
                        st.dataframe(
                            df_residuales_bdd[[
                                "agente", 
                                "dependencia_general",
                                "formulario", 
                                "calificacion", 
                                "puntaje_total",
                                "puntaje_relativo", 
                                "recibe_bdd"
                            ]].rename(columns={
                                "agente": "AGENTE",
                                "dependencia_general": "DEPENDENCIA",
                                "formulario": "NIVEL",
                                "calificacion": "CALIFICACIÓN",
                                "puntaje_total": "PUNTAJE TOTAL",
                                "puntaje_relativo": "PUNTAJE RELATIVO",
                                "recibe_bdd": "RECIBE BDD"
                            }),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Mostrar advertencias si hay empates
                        if total_residuales_destacado > cupo_residual:
                            # Verificar si hay empates en el límite
                            if cupo_residual > 0:
                                puntaje_corte = df_residuales_bdd.iloc[cupo_residual-1]["puntaje_relativo"]
                                empates = df_residuales_bdd[df_residuales_bdd["puntaje_relativo"] == puntaje_corte]
                                
                                if len(empates) > 1:
                                    st.warning(f"⚠️ Hay {len(empates)} agentes empatados con puntaje {puntaje_corte:.3f}. El superior debe desempatar.")
                                    st.dataframe(empates[["agente", "puntaje_relativo"]])
                
                # Mostrar resumen global de BDD al final
                st.markdown("---")
                st.markdown("### 📈 Resumen Global de Elegibles BDD")
                
                # Obtener todas las dependencias
                dependencias = df["dependencia_general"].dropna().unique()
                resumen_global = []
                
                for dep in dependencias:
                    df_dep = df[df["dependencia_general"] == dep]
                    total_dep = len(df_dep[df_dep["anulada"] != True])
                    elegibles_dep = len(df_dep[
                        (df_dep["calificacion"] == "DESTACADO") & 
                        (df_dep["residual"] == False) & 
                        (df_dep["anulada"] != True)
                    ])
                    bonificados_dep = len(df_dep[df_dep["bonificacion_elegible"] == True])
                    cupo_dep = max(1, int(total_dep * 0.1))
                    
                    resumen_global.append({
                        "DEPENDENCIA": dep,
                        "TOTAL_EVALUADOS": total_dep,
                        "ELEGIBLES_DESTACADO": elegibles_dep,
                        "CUPO_BDD_10%": cupo_dep,
                        "BONIFICADOS_EFECTIVOS": bonificados_dep
                    })
                
                df_resumen = pd.DataFrame(resumen_global)
                st.dataframe(df_resumen, use_container_width=True, hide_index=True)
                
                # Métricas totales
                total_bonificados = df_resumen["BONIFICADOS_EFECTIVOS"].sum()
                total_evaluados_global = df_resumen["TOTAL_EVALUADOS"].sum()
                
                # Agregar bonificaciones residuales al total
                bonificados_residuales = len(df[
                    (df["residual"] == True) & 
                    (df["bonificacion_elegible"] == True)
                ])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🏆 Bonificaciones Dependencias", total_bonificados)
                with col2:
                    st.metric("🔄 Bonificaciones Residuales", bonificados_residuales)
                with col3:
                    total_final = total_bonificados + bonificados_residuales
                    st.metric("🎯 TOTAL BONIFICACIONES", total_final)

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


