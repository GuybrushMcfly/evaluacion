import streamlit as st
import pandas as pd
from pytz import timezone
import time

# ---- Vista: Evaluaciones ----
def mostrar(supabase):
    st.header("📋 Evaluaciones realizadas")

    # Obtener agente actual
    usuario = st.session_state.get("usuario", "")
    dependencia_usuario = st.session_state.get("dependencia", "")
    dependencia_general = st.session_state.get("dependencia_general", "")
    dependencias_subordinadas = st.session_state.get("dependencias_subordinadas", [])

    # Armar opciones de filtro
    opciones_dependencia = []
    if dependencia_general:
        opciones_dependencia.append(f"{dependencia_general} (todas)")
    if dependencia_usuario:
        opciones_dependencia.append(f"{dependencia_usuario} (individual)")
    opciones_dependencia += [d for d in dependencias_subordinadas if d != dependencia_usuario]

    dependencia_seleccionada = st.selectbox("📂 Dependencia a visualizar:", opciones_dependencia)

    # Filtrar agentes por dependencia seleccionada
    if "(todas)" in dependencia_seleccionada:
        dependencia_filtro = dependencia_general
        agentes = supabase.table("agentes").select("cuil, evaluado_2024").eq("dependencia_general", dependencia_filtro).execute().data
    elif "(individual)" in dependencia_seleccionada:
        dependencia_filtro = dependencia_usuario
        agentes = supabase.table("agentes").select("cuil, evaluado_2024").eq("dependencia", dependencia_filtro).execute().data
    else:
        dependencia_filtro = dependencia_seleccionada
        agentes = supabase.table("agentes").select("cuil, evaluado_2024").eq("dependencia", dependencia_filtro).execute().data

    cuils_asignados = [a["cuil"] for a in agentes]

    total_asignados = len(cuils_asignados)
    evaluados = sum(1 for a in agentes if a.get("evaluado_2024") is True)
    porcentaje = (evaluados / total_asignados * 100) if total_asignados > 0 else 0

    st.divider()
    st.subheader("📊 Indicadores")
    cols = st.columns(3)
    with cols[0]: st.metric("Total para evaluar", total_asignados)
    with cols[1]: st.metric("Evaluados", evaluados)
    with cols[2]: st.metric("% Evaluados", f"{porcentaje:.1f}%")
    st.progress(min(100, int(porcentaje)), text=f"Progreso de evaluaciones registradas: {porcentaje:.1f}%")

    # Obtener evaluaciones filtradas
    evaluaciones = supabase.table("evaluaciones").select("*").in_("cuil", cuils_asignados).execute().data
    df_eval = pd.DataFrame(evaluaciones)
    if not df_eval.empty:
        hora_arg = timezone('America/Argentina/Buenos_Aires')
        df_eval["Fecha"] = pd.to_datetime(df_eval["fecha_evaluacion"], utc=True).dt.tz_convert(hora_arg)
        df_eval["Fecha_formateada"] = df_eval["Fecha"].dt.strftime('%d/%m/%Y %H:%M')
        df_eval["anulada"] = df_eval["anulada"].fillna(False)
        df_eval["Estado"] = df_eval["anulada"].apply(lambda x: "Anulada" if x else "Registrada")
    else:
        df_eval = pd.DataFrame(columns=["formulario", "calificacion"])

    # Tabla de formularios
    st.subheader("📋 Uso de formularios")
    if not df_eval.empty:
        st.dataframe(df_eval["formulario"].value_counts().rename_axis("Formulario").reset_index(name="Cantidad"), use_container_width=True, hide_index=True)
    else:
        st.info("No hay formularios registrados aún.")

    # Tabla de calificaciones
    st.subheader("📋 Distribución por calificación")
    if not df_eval.empty:
        st.dataframe(df_eval["calificacion"].value_counts().rename_axis("Calificación").reset_index(name="Cantidad"), use_container_width=True, hide_index=True)
    else:
        st.info("No hay calificaciones registradas aún.")

    # ---- BLOQUE DE NO ANULADAS ----
    df_no_anuladas = df_eval[df_eval["anulada"] == False].copy()
    if not df_no_anuladas.empty:
        st.subheader("🔄 Evaluaciones que pueden anularse:")
        df_no_anuladas["Seleccionar"] = False
        df_no_anuladas = df_no_anuladas[[
            "Seleccionar", "id_evaluacion", "cuil", "apellido_nombre", 
            "formulario", "calificacion", "puntaje_total", "evaluador", "Fecha_formateada", "Estado"
        ]]

        df_para_mostrar = df_no_anuladas[[
            "Seleccionar", "apellido_nombre", "formulario",
            "calificacion", "puntaje_total", "evaluador", "Fecha_formateada", "Estado"
        ]].rename(columns={
            "Seleccionar": "Seleccionar",
            "apellido_nombre": "Apellido y Nombres",
            "formulario": "Form.",
            "calificacion": "Calificación",
            "puntaje_total": "Puntaje",
            "evaluador": "Evaluador",
            "Fecha_formateada": "Fecha",
            "Estado": "Estado"
        })

        seleccion = st.data_editor(
            df_para_mostrar,
            use_container_width=True,
            hide_index=True,
            disabled=["Apellido y Nombres", "Form.", "Calificación", "Puntaje", "Evaluador", "Fecha", "Estado"],
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

    # ---- BLOQUE DE ANULADAS ----
    df_anuladas = df_eval[df_eval["anulada"]].copy()
    if not df_anuladas.empty:
        st.subheader("❌ Evaluaciones ya anuladas:")
        st.dataframe(
            df_anuladas[[
                "apellido_nombre", "formulario",
                "calificacion", "puntaje_total", "evaluador",
                "Fecha_formateada", "Estado"
            ]].rename(columns={
                "apellido_nombre": "Apellido y Nombres",
                "formulario": "Form.",
                "calificacion": "Calificación",
                "puntaje_total": "Puntaje",
                "evaluador": "Evaluador",
                "Fecha_formateada": "Fecha",
                "Estado": "Estado"
            }),
            use_container_width=True,
            hide_index=True
