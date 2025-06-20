import streamlit as st
import pandas as pd
from pytz import timezone
import time

def mostrar(supabase):
    st.markdown("<h2 style='font-size:26px;'>📋 Evaluaciones realizadas</h2>", unsafe_allow_html=True)
    
    # --- Función para verificar rol activo ---
    def tiene_rol(*roles):
        return any(st.session_state.get("rol", {}).get(r, False) for r in roles)

    dependencia_usuario = st.session_state.get("dependencia", "")
    dependencia_general = st.session_state.get("dependencia_general", "")

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

    # --- Filtrar agentes por dependencia seleccionada ---
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

    st.divider()
    st.markdown("<h2 style='font-size:24px;'>📊 Indicadores</h2>", unsafe_allow_html=True)

    # --- Obtener y procesar evaluaciones ---
    # --- Obtener y procesar evaluaciones ---
    evaluaciones = supabase.table("evaluaciones").select("*").in_("cuil", cuils_asignados).execute().data
    df_eval = pd.DataFrame(evaluaciones)
    
    if df_eval.empty:
        df_eval = pd.DataFrame(columns=[
            "formulario", "calificacion", "anulada", "fecha_evaluacion", "apellido_nombre",
            "puntaje_total", "evaluador", "id_evaluacion", "cuil"
        ])
    
    # Normalizar columna anulada
    if "anulada" not in df_eval.columns:
        df_eval["anulada"] = False
    else:
        df_eval["anulada"] = df_eval["anulada"].fillna(False).astype(bool)
    
    # --- Solo evaluaciones NO anuladas, última por CUIL ---
    df_no_anuladas = df_eval[df_eval["anulada"] == False].copy()
    
    if "fecha_evaluacion" in df_no_anuladas.columns and not df_no_anuladas["fecha_evaluacion"].isna().all():
        df_no_anuladas["fecha_evaluacion"] = pd.to_datetime(df_no_anuladas["fecha_evaluacion"], errors="coerce")
        df_no_anuladas = df_no_anuladas.sort_values("fecha_evaluacion").drop_duplicates("cuil", keep="last")
    elif "id_evaluacion" in df_no_anuladas.columns:
        df_no_anuladas = df_no_anuladas.sort_values("id_evaluacion").drop_duplicates("cuil", keep="last")
    
    # Asegurá que existan todas las columnas requeridas
    columnas_tabla = ["apellido_nombre", "formulario", "calif_puntaje", "evaluador", "Fecha_formateada"]
    for col in columnas_tabla:
        if col not in df_no_anuladas.columns:
            df_no_anuladas[col] = ""
    
    # Calcular columna de puntaje si no existe o está vacía
    if df_no_anuladas["calif_puntaje"].isnull().all() or (df_no_anuladas["calif_puntaje"] == "").all():
        df_no_anuladas["calif_puntaje"] = df_no_anuladas.apply(
            lambda row: f"{row.get('calificacion','')} ({row.get('puntaje_total','')})"
            if pd.notna(row.get("calificacion")) and pd.notna(row.get("puntaje_total"))
            else "",
            axis=1
        )
    
    # Calcular fecha formateada
    if "fecha_evaluacion" in df_no_anuladas.columns and not df_no_anuladas["fecha_evaluacion"].isna().all():
        hora_arg = timezone('America/Argentina/Buenos_Aires')
        df_no_anuladas["Fecha"] = pd.to_datetime(df_no_anuladas["fecha_evaluacion"], errors="coerce", utc=True).dt.tz_convert(hora_arg)
        df_no_anuladas["Fecha_formateada"] = df_no_anuladas["Fecha"].dt.strftime('%d/%m/%Y %H:%M')
    else:
        df_no_anuladas["Fecha_formateada"] = ""
    
    # Asignar estado
    df_no_anuladas["Estado"] = "Registrada"


    # --- Indicadores únicos por persona ---
    evaluados = len(df_no_anuladas["cuil"].unique())
    porcentaje = (evaluados / total_asignados * 100) if total_asignados > 0 else 0

    cols = st.columns(3)
    with cols[0]: st.metric("👥 Total a Evaluar", total_asignados)
    with cols[1]: st.metric("✅ Evaluados", evaluados)
    with cols[2]: st.metric("📊 % Evaluación", f"{round(porcentaje)}%")
    st.progress(min(100, int(porcentaje)), text=f"Progreso de evaluaciones registradas: {porcentaje:.1f}%")

    # --- Calificaciones únicas por cuil ---
    st.markdown("<h2 style='font-size:24px;'>📋 Distribución de evaluaciones según calificación</h2>", unsafe_allow_html=True)
    categorias = ["DESTACADO", "BUENO", "REGULAR", "DEFICIENTE"]
    calif_counts = {cat: 0 for cat in categorias}
    if not df_no_anuladas.empty and "calificacion" in df_no_anuladas.columns:
        temp_counts = df_no_anuladas["calificacion"].value_counts()
        for cat in categorias:
            calif_counts[cat] = temp_counts.get(cat, 0)
    col_cats = st.columns(len(categorias))
    emojis = ["🌟", "👍", "🟡", "🔴"]
    for i, cat in enumerate(categorias):
        col_cats[i].metric(f"{emojis[i]} {cat.title()}", calif_counts[cat])

    # --- Niveles jerárquicos agrupados por formulario ---
    st.markdown("<h2 style='font-size:24px;'>📋 Distribución por nivel de evaluación</h2>", unsafe_allow_html=True)
    
    # Asegurar que formulario esté como string
    df_no_anuladas["formulario"] = df_no_anuladas["formulario"].astype(str)
    
    # Conteos por formulario
    conteo_form = df_no_anuladas["formulario"].value_counts()
    
    # Agrupación por nivel
    nivel_gerencial = conteo_form.get("1", 0)
    nivel_medio = sum(conteo_form.get(str(f), 0) for f in [2, 3, 4])
    nivel_operativo = sum(conteo_form.get(str(f), 0) for f in [5, 6])
    
    # Mostrar indicadores
    cols_niveles = st.columns(3)
    cols_niveles[0].metric("🔵 Nivel Jerárquico", nivel_gerencial)
    cols_niveles[1].metric("🟢 Nivel Medio", nivel_medio)
    cols_niveles[2].metric("🟣 Nivel Operativo", nivel_operativo)


    st.markdown("<br><br>", unsafe_allow_html=True)  # Espacio más grande

    # ---- TABLA DE EVALUACIONES REGISTRADAS ----
    st.markdown("<h2 style='font-size:24px;'>✅ Evaluaciones registradas:</h2>", unsafe_allow_html=True)
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
        st.markdown("<h2 style='font-size:24px;'>🔄 Evaluaciones que pueden anularse:</h2>", unsafe_allow_html=True)
    
        # Aseguramos que existan las columnas necesarias
        for col in ["Seleccionar", "calif_puntaje", "apellido_nombre", "formulario",
                    "evaluador", "Fecha_formateada", "Estado", "id_evaluacion", "cuil", "calificacion", "puntaje_total"]:
            if col not in df_no_anuladas.columns:
                if col == "Seleccionar":
                    df_no_anuladas["Seleccionar"] = False
                else:
                    df_no_anuladas[col] = ""
    
        # Crear calif_puntaje (siempre seguro)
        df_no_anuladas["calif_puntaje"] = df_no_anuladas.apply(
            lambda row: f"{row['calificacion']} ({row['puntaje_total']})"
            if row.get("calificacion") and row.get("puntaje_total") else "",
            axis=1
        )
    
        # Para mostrar, solo las columnas necesarias (y crearlas si faltan)
        columnas_mostrar = [
            "Seleccionar", "apellido_nombre", "formulario",
            "calif_puntaje", "evaluador", "Fecha_formateada", "Estado", "id_evaluacion"
        ]
        for col in columnas_mostrar:
            if col not in df_no_anuladas.columns:
                df_no_anuladas[col] = ""
        df_para_mostrar = df_no_anuladas[columnas_mostrar].rename(columns={
            "Seleccionar": "Seleccionar",
            "apellido_nombre": "Apellido y Nombres",
            "formulario": "Form.",
            "calif_puntaje": "Calificación/Puntaje",
            "evaluador": "Evaluador",
            "Fecha_formateada": "Fecha",
            "Estado": "Estado",
            "id_evaluacion": "id_evaluacion"
        })
    
        # Editor de tabla
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
                    eval_sel = df_no_anuladas[df_no_anuladas["id_evaluacion"] == id_eval]
                    if not eval_sel.empty:
                        cuil_sel = str(eval_sel.iloc[0].get("cuil", "")).strip()
                        supabase.table("evaluaciones").update({"anulada": True})\
                            .eq("id_evaluacion", id_eval).execute()
                        if cuil_sel:
                            supabase.table("agentes").update({"evaluado_2024": False})\
                                .eq("cuil", cuil_sel).execute()
                st.success(f"✅ {len(ids_seleccionados)} evaluaciones anuladas.")
                time.sleep(2)
                st.rerun()
    
    # TABLA DE ANULADAS
    df_anuladas = df_eval[df_eval["anulada"] == True].copy()
    # Calcular Fecha formateada en anuladas
    df_anuladas["fecha_evaluacion"] = pd.to_datetime(df_anuladas["fecha_evaluacion"], errors="coerce")
    df_anuladas["Fecha_formateada"] = df_anuladas["fecha_evaluacion"].dt.strftime('%d/%m/%Y %H:%M')

    if not df_anuladas.empty:
        # Asegurar columnas
        for col in ["calif_puntaje", "apellido_nombre", "formulario", "evaluador", "Fecha_formateada", "Estado"]:
            if col not in df_anuladas.columns:
                df_anuladas[col] = ""
        df_anuladas["calif_puntaje"] = df_anuladas.apply(
            lambda row: f"{row['calificacion']} ({row['puntaje_total']})" if row.get("calificacion") and row.get("puntaje_total") else "",
            axis=1
        )
        st.markdown("<h2 style='font-size:24px;'>❌ Evaluaciones ya anuladas:</h2>", unsafe_allow_html=True)
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
