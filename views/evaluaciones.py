import streamlit as st
import pandas as pd
from pytz import timezone
import time

# ---- Vista: Evaluaciones ----
def mostrar(supabase):
    #st.header("📋 Evaluaciones realizadas")
    st.markdown("<h2 style='font-size:24px;'>📋 Evaluaciones realizadas</h1>", unsafe_allow_html=True)
    
    # Función para verificar rol activo
    def tiene_rol(*roles):
        return any(st.session_state.get("rol", {}).get(r, False) for r in roles)

    # Rol y dependencias desde sesión
    dependencia_usuario = st.session_state.get("dependencia", "")
    dependencia_general = st.session_state.get("dependencia_general", "")

    # Construir opciones de filtro de dependencia
    opciones_dependencia = []

    if tiene_rol("rrhh", "coordinador", "evaluador_general") and dependencia_general:
        opciones_dependencia.append(f"{dependencia_general} (todas)")

    if dependencia_usuario:
        opciones_dependencia.append(f"{dependencia_usuario} (individual)")

    dependencias_subordinadas = []
    if tiene_rol("rrhh", "coordinador", "evaluador_general") and dependencia_general:
        resultado = supabase.table("unidades_evaluacion")\
            .select("dependencia")\
            .eq("dependencia_general", dependencia_general)\
            .neq("dependencia", dependencia_usuario)\
            .execute()
        dependencias_subordinadas = sorted({d["dependencia"] for d in resultado.data})
        opciones_dependencia += [
            d for d in dependencias_subordinadas
            if d != dependencia_usuario and "UNIDAD RESIDUAL" not in d.upper()
        ]

    dependencia_seleccionada = st.selectbox("📂 Dependencia a visualizar:", opciones_dependencia)

    # Filtrar agentes por dependencia seleccionada
    if dependencia_seleccionada and "(todas)" in dependencia_seleccionada:
        dependencia_filtro = dependencia_general
        agentes = supabase.table("agentes").select("cuil, evaluado_2024").eq("dependencia_general", dependencia_filtro).execute().data
    elif dependencia_seleccionada and "(individual)" in dependencia_seleccionada:
        dependencia_filtro = dependencia_usuario
        agentes = supabase.table("agentes").select("cuil, evaluado_2024").eq("dependencia", dependencia_filtro).execute().data
    elif dependencia_seleccionada:
        dependencia_filtro = dependencia_seleccionada
        agentes = supabase.table("agentes").select("cuil, evaluado_2024").eq("dependencia", dependencia_filtro).execute().data
    else:
        st.warning("⚠️ Seleccione una dependencia válida para continuar.")
        return

    cuils_asignados = [a["cuil"] for a in agentes]
    total_asignados = len(cuils_asignados)
    evaluados = sum(1 for a in agentes if a.get("evaluado_2024") is True)
    porcentaje = (evaluados / total_asignados * 100) if total_asignados > 0 else 0

    st.divider()
    #st.subheader("📊 Indicadores")
    st.markdown("<h2 style='font-size:24px;'>📊 Indicadores</h2>", unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]: st.metric("Total para evaluar", total_asignados)
    with cols[1]: st.metric("Evaluados", evaluados)
    with cols[2]: st.metric("% Evaluados", f"{porcentaje:.1f}%")
    st.progress(min(100, int(porcentaje)), text=f"Progreso de evaluaciones registradas: {porcentaje:.1f}%")

    # Obtener evaluaciones filtradas
    evaluaciones = supabase.table("evaluaciones").select("*").in_("cuil", cuils_asignados).execute().data
    df_eval = pd.DataFrame(evaluaciones)

    if df_eval.empty:
        df_eval = pd.DataFrame(columns=[
            "formulario", "calificacion", "anulada", "fecha_evaluacion", "apellido_nombre",
            "puntaje_total", "evaluador", "id_evaluacion", "cuil"
        ])

    if "anulada" not in df_eval.columns:
        df_eval["anulada"] = False
    else:
        df_eval["anulada"] = df_eval["anulada"].fillna(False).astype(bool)

    if "fecha_evaluacion" in df_eval.columns and not df_eval["fecha_evaluacion"].isna().all():
        hora_arg = timezone('America/Argentina/Buenos_Aires')
        df_eval["Fecha"] = pd.to_datetime(df_eval["fecha_evaluacion"], utc=True).dt.tz_convert(hora_arg)
        df_eval["Fecha_formateada"] = df_eval["Fecha"].dt.strftime('%d/%m/%Y %H:%M')
    else:
        df_eval["Fecha_formateada"] = ""

    df_eval["Estado"] = df_eval["anulada"].apply(lambda x: "Anulada" if x else "Registrada")
    df_no_anuladas = df_eval[df_eval["anulada"] == False].copy()

    #st.subheader("📋 Uso de formularios")
    st.markdown("<h2 style='font-size:24px;'>📋 Uso de formularios</h2>", unsafe_allow_html=True)
    form_labels = ["1", "2", "3", "4", "5", "6"]
    form_columnas = {f"FORM. {f}": [0] for f in form_labels}

    if not df_no_anuladas.empty and "formulario" in df_no_anuladas.columns:
        df_no_anuladas["formulario"] = df_no_anuladas["formulario"].astype(str)
        formulario_counts = df_no_anuladas["formulario"].value_counts()
        for f in form_labels:
            form_columnas[f"FORM. {f}"] = [formulario_counts.get(f, 0)]
    df_form = pd.DataFrame(form_columnas)
    st.dataframe(df_form, use_container_width=True, hide_index=True)

#    st.subheader("📋 Distribución por calificación")
    st.markdown("<h2 style='font-size:24px;'>📋 Distribución por calificación</h2>", unsafe_allow_html=True)
    categorias = ["DESTACADO", "BUENO", "REGULAR", "DEFICIENTE"]
    calif_columnas = {cat: [0] for cat in categorias}

    if not df_no_anuladas.empty and "calificacion" in df_no_anuladas.columns:
        calif_counts = df_no_anuladas["calificacion"].value_counts()
        for cat in categorias:
            calif_columnas[cat] = [calif_counts.get(cat, 0)]
    df_calif = pd.DataFrame(calif_columnas)
    st.dataframe(df_calif, use_container_width=True, hide_index=True)

    if not df_no_anuladas.empty:
        df_no_anuladas["calif_puntaje"] = df_no_anuladas.apply(
            lambda row: f"{row['calificacion']} ({row['puntaje_total']})", axis=1
        )

        st.subheader("✅ Evaluaciones registradas:")
        st.dataframe(
            df_no_anuladas[[
                "apellido_nombre", "formulario", "calif_puntaje", "evaluador", "Fecha_formateada"
            ]].rename(columns={
                "apellido_nombre": "Apellido y Nombres",
                "formulario": "Form.",
                "calif_puntaje": "Calificación/Puntaje",
                "evaluador": "Evaluador",
                "Fecha_formateada": "Fecha"
            }),
            use_container_width=True,
            hide_index=True
        )

    
    if not df_no_anuladas.empty:
        st.subheader("🔄 Evaluaciones que pueden anularse:")
        df_no_anuladas["Seleccionar"] = False
        df_no_anuladas["calif_puntaje"] = df_no_anuladas.apply(
            lambda row: f"{row['calificacion']} ({row['puntaje_total']})", axis=1
        )
    
        # Incluí id_evaluacion antes de construir df_para_mostrar
       # Incluí id_evaluacion antes de construir df_para_mostrar
        df_para_mostrar = df_no_anuladas[[
            "Seleccionar", "apellido_nombre", "formulario",
            "calif_puntaje", "evaluador", "Fecha_formateada", "Estado", "id_evaluacion"
        ]].rename(columns={
            "Seleccionar": "Seleccionar",
            "apellido_nombre": "Apellido y Nombres",
            "formulario": "Form.",
            "calif_puntaje": "Calificación/Puntaje",
            "evaluador": "Evaluador",
            "Fecha_formateada": "Fecha",
            "Estado": "Estado",
            "id_evaluacion": "id_evaluacion"
        })
        
        # Editor con id_evaluacion oculta pero disponible
        seleccion = st.data_editor(
            df_para_mostrar,
            use_container_width=True,
            hide_index=True,
            disabled=[
                "Apellido y Nombres", "Form.", "Calificación/Puntaje",
                "Evaluador", "Fecha", "Estado", "id_evaluacion"
            ],
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn("Seleccionar"),
                "id_evaluacion": None  # ⛔ Oculta visualmente esta columna
            }
        )
        
        # Botón para anular seleccionadas
        if st.button("❌ Anular seleccionadas"):
            if "Seleccionar" in seleccion.columns:
                seleccionados = seleccion[seleccion["Seleccionar"] == True]
                ids_seleccionados = seleccionados["id_evaluacion"].tolist()
            else:
                ids_seleccionados = []
        
            if not ids_seleccionados:
                st.warning("⚠️ No hay evaluaciones seleccionadas para anular.")
            else:
                for id_eval in ids_seleccionados:
                    eval_sel = df_no_anuladas[df_no_anuladas["id_evaluacion"] == id_eval].iloc[0]
                    supabase.table("evaluaciones").update({"anulada": True})\
                        .eq("id_evaluacion", id_eval).execute()
                    supabase.table("agentes").update({"evaluado_2024": False})\
                        .eq("cuil", str(eval_sel["cuil"]).strip()).execute()
                st.success(f"✅ {len(ids_seleccionados)} evaluaciones anuladas.")
                time.sleep(2)
                st.rerun()


    df_anuladas = df_eval[df_eval["anulada"] == True].copy()
    if not df_anuladas.empty:
        df_anuladas["calif_puntaje"] = df_anuladas.apply(
            lambda row: f"{row['calificacion']} ({row['puntaje_total']})", axis=1
        )

        st.subheader("❌ Evaluaciones ya anuladas:")
        st.dataframe(
            df_anuladas[[
                "apellido_nombre", "formulario",
                "calif_puntaje", "evaluador",
                "Fecha_formateada", "Estado"
            ]].rename(columns={
                "apellido_nombre": "Apellido y Nombres",
                "formulario": "Form.",
                "calif_puntaje": "Calificación/Puntaje",
                "evaluador": "Evaluador",
                "Fecha_formateada": "Fecha",
                "Estado": "Estado"
            }),
            use_container_width=True,
            hide_index=True
        )
