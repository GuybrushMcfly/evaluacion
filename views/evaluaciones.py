import streamlit as st
import pandas as pd
from pytz import timezone
import time

def mostrar(supabase):
    st.markdown("<a id='evaluaciones'></a>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 60px;'></div>", unsafe_allow_html=True)
    st.markdown("#### 📋 Evaluaciones realizadas")

    # Cargar datos
    evaluaciones = supabase.table("evaluaciones").select("*").execute().data
    if not evaluaciones:
        st.warning("⚠️ No hay evaluaciones registradas.")
        return

    df = pd.DataFrame(evaluaciones)

    # Filtros iniciales
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        ingresante = st.selectbox("🔹 Ingresante", ["Todos", "Sí", "No"])
    with col2:
        formularios = sorted(df["formulario"].dropna().unique())
        formulario = st.selectbox("🔹 Formulario", ["Todos"] + formularios)
    with col3:
        calificaciones = sorted(df["calificacion"].dropna().unique())
        calificacion = st.selectbox("🔹 Calificación", ["Todos"] + calificaciones)

    # Aplicar filtros
    df_filt = df.copy()
    if ingresante != "Todos":
        df_filt = df_filt[df_filt["ingresante"] == (ingresante == "Sí")]
    if formulario != "Todos":
        df_filt = df_filt[df_filt["formulario"] == formulario]
    if calificacion != "Todos":
        df_filt = df_filt[df_filt["calificacion"] == calificacion]

    # Sección de métricas
    st.divider()
    st.subheader("📊 Indicadores")
    total = len(df_filt)
    anuladas = df_filt["anulada"].fillna(False).sum()
    registradas = total - anuladas
    porcentaje = (registradas / total * 100) if total else 0

    cols = st.columns(3)
    with cols[0]: st.metric("Total evaluaciones", total)
    with cols[1]: st.metric("Registradas", registradas)
    with cols[2]: st.metric("% Registradas", f"{porcentaje:.1f}%")

    st.progress(min(100, int(porcentaje)), text=f"Progreso de evaluaciones registradas: {porcentaje:.1f}%")

    # Expandible con tabla completa
    columnas_fijas = ["apellido_nombre", "formulario", "calificacion", "puntaje_total", "evaluador", "fecha_evaluacion"]
    with st.expander("📋 LISTADO DE EVALUACIONES", expanded=True):
        columnas_seleccionadas = st.multiselect(
            "Seleccionar columnas a mostrar:",
            options=columnas_fijas,
            default=columnas_fijas
        )

        hora_arg = timezone('America/Argentina/Buenos_Aires')
        df_filt["fecha_evaluacion"] = pd.to_datetime(df_filt["fecha_evaluacion"], utc=True).dt.tz_convert(hora_arg)
        df_filt["Fecha_formateada"] = df_filt["fecha_evaluacion"].dt.strftime('%d/%m/%Y %H:%M')

        if columnas_seleccionadas:
            df_mostrar = df_filt[columnas_seleccionadas].copy()
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("Seleccioná al menos una columna para mostrar.")

    # Bloque de anulaciones
    st.divider()
    st.subheader("❌ Gestión de anulaciones")
    df_filt["anulada"] = df_filt["anulada"].fillna(False)
    df_filt["Estado"] = df_filt["anulada"].apply(lambda x: "Anulada" if x else "Registrada")

    columnas_visibles = [
        "Seleccionar", "apellido_nombre", "formulario",
        "calificacion", "puntaje_total", "evaluador", "Fecha_formateada", "Estado"
    ]
    renombrar_columnas = {
        "Seleccionar": "Seleccionar",
        "apellido_nombre": "Apellido y Nombres",
        "formulario": "Form.",
        "calificacion": "Calificación",
        "puntaje_total": "Puntaje",
        "evaluador": "Evaluador",
        "Fecha_formateada": "Fecha",
        "Estado": "Estado"
    }

    df_no_anuladas = df_filt[df_filt["anulada"] == False].copy()
    if not df_no_anuladas.empty:
        df_no_anuladas["Seleccionar"] = False
        df_no_anuladas = df_no_anuladas[[
            "Seleccionar", "id_evaluacion", "cuil", "apellido_nombre", 
            "formulario", "calificacion", "puntaje_total", "evaluador", "Fecha_formateada", "Estado"
        ]]

        df_para_mostrar = df_no_anuladas[[
            "Seleccionar", "apellido_nombre", "formulario",
            "calificacion", "puntaje_total", "evaluador", "Fecha_formateada", "Estado"
        ]].rename(columns=renombrar_columnas)

        seleccion = st.data_editor(
            df_para_mostrar,
            use_container_width=True,
            hide_index=True,
            disabled=columnas_visibles[1:],
            column_config={"Seleccionar": st.column_config.CheckboxColumn("Seleccionar")}
        )

        if st.button("❌ Anular seleccionadas"):
            indices = seleccion[seleccion["Seleccionar"]].reset_index().index
            if len(indices) == 0:
                st.warning("⚠️ No hay evaluaciones seleccionadas para anular.")
            else:
                df_no_anuladas.reset_index(drop=True, inplace=True)
                for idx in indices:
                    eval_sel = df_no_anuladas.iloc[idx]
                    supabase.table("evaluaciones").update({"anulada": True})\
                        .eq("id_evaluacion", eval_sel["id_evaluacion"]).execute()
                    supabase.table("agentes").update({"evaluado_2024": False})\
                        .eq("cuil", str(eval_sel["cuil"]).strip()).execute()
                st.success(f"✅ {len(indices)} evaluaciones anuladas.")
                time.sleep(2)
                st.rerun()

    df_anuladas = df_filt[df_filt["anulada"]].copy()
    if not df_anuladas.empty:
        st.subheader("🗂️ Evaluaciones anuladas")
        st.dataframe(
            df_anuladas[[
                "apellido_nombre", "formulario",
                "calificacion", "puntaje_total", "evaluador",
                "Fecha_formateada", "Estado"
            ]].rename(columns={k: v for k, v in renombrar_columnas.items() if k != "Seleccionar"}),
            use_container_width=True,
            hide_index=True
        )
