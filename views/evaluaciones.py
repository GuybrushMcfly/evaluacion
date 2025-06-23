import streamlit as st
import pandas as pd
from pytz import timezone
import time
import tempfile
import io

from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

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
    st.markdown("<h2 style='font-size:24px;'>📋 Distribución por Calificación</h2>", unsafe_allow_html=True)
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
    st.markdown("<h2 style='font-size:24px;'>📋 Distribución por Nivel de Evaluación</h2>", unsafe_allow_html=True)
    
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

    # ---- BOTÓN PARA GENERAR Y DESCARGAR INFORME WORD ----


    st.markdown("---")
    st.markdown("<h3 style='font-size:22px;'>📄 Generar informe resumen</h3>", unsafe_allow_html=True)

    def set_cell_style(cell, bold=True, bg_color="D9D9D9"):
        """Aplica estilo Calibri 10 y fondo gris a una celda"""
        para = cell.paragraphs[0]
        run = para.runs[0] if para.runs else para.add_run()
        run.font.name = "Calibri"
        run.font.size = Pt(11)
        run.font.bold = bold
    
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), bg_color)
        tcPr.append(shd)
    
    def generar_planilla_docx(df, dependencia_nombre):
        doc = Document()
    
        # Fuente por defecto del documento
        style = doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
    
        # Encabezado
        doc.add_heading("INSTITUTO NACIONAL DE ESTADISTICA Y CENSOS", level=1)
        doc.add_paragraph("DIRECCIÓN DE CAPACITACIÓN Y CARRERA DE PERSONAL")
        doc.add_paragraph("EVALUACIÓN DE DESEMPEÑO 2024")
        doc.add_heading(f"UNIDAD DE ANALISIS: {dependencia_nombre}", level=2)
    
        # --- AGRUPAMIENTO ---
        doc.add_heading("PERSONAL POR TIPO DE AGRUPAMIENTO", level=2)
        gral = len(df[df["agrupamiento"] == "GRAL"])
        prof = len(df[df["agrupamiento"] == "PROF"])
        tabla_agrup = doc.add_table(rows=2, cols=2)
        tabla_agrup.style = 'Table Grid'
        headers = ["GENERAL", "PROFESIONAL"]
        for i, h in enumerate(headers):
            tabla_agrup.cell(0, i).text = h
            set_cell_style(tabla_agrup.cell(0, i))
            tabla_agrup.cell(1, i).text = str([gral, prof][i])
    
        # --- NIVEL ESCALAFONARIO ---
        doc.add_heading("PERSONAL POR TIPO DE NIVEL ESCALAFONARIO", level=2)
        niveles = ["A", "B", "C", "D", "E"]
        conteo_niveles = df["nivel"].value_counts()
        tabla_nivel = doc.add_table(rows=2, cols=5)
        tabla_nivel.style = 'Table Grid'
        for i, nivel in enumerate(niveles):
            tabla_nivel.cell(0, i).text = nivel
            set_cell_style(tabla_nivel.cell(0, i))
            tabla_nivel.cell(1, i).text = str(conteo_niveles.get(nivel, 0))
    
        # --- PERSONAL EVALUADO ---
        doc.add_heading("PERSONAL EVALUADO", level=2)
        df_evaluable = df[df["ingresante"].isin([True, False])]
        no_ingresantes = len(df_evaluable[df_evaluable["ingresante"] == False])
        ingresantes = len(df_evaluable[df_evaluable["ingresante"] == True])
        total_evaluable = no_ingresantes + ingresantes
        total_evaluado = df["cuil"].nunique()
    
        tabla_eval = doc.add_table(rows=2, cols=4)
        tabla_eval.style = 'Table Grid'
        eval_headers = [
            "PERMANENTES NO INGRESANTE",
            "PERMANENTES INGRESANTES",
            "TOTAL A EVALUAR",
            "TOTAL EVALUADO"
        ]
        for i, h in enumerate(eval_headers):
            tabla_eval.cell(0, i).text = h
            set_cell_style(tabla_eval.cell(0, i))
            tabla_eval.cell(1, i).text = str([no_ingresantes, ingresantes, total_evaluable, total_evaluado][i])
    
        # --- EVALUACIONES POR FORMULARIO ---
        def agregar_tabla_por_formulario(titulo, formularios):
            doc.add_heading(titulo, level=2)
            subset = df[df["formulario"].astype(str).isin(formularios)].sort_values("apellido_nombre")
            tabla = doc.add_table(rows=1, cols=3)
            tabla.style = 'Table Grid'
            cols = ["APELLIDOS Y NOMBRES", "CALIFICACIÓN", "PUNTAJE"]
            for i, c in enumerate(cols):
                tabla.cell(0, i).text = c
                set_cell_style(tabla.cell(0, i))
            for _, row in subset.iterrows():
                r = tabla.add_row().cells
                r[0].text = row.get("apellido_nombre", "")
                r[1].text = row.get("calificacion", "")
                r[2].text = str(row.get("puntaje_total", ""))
    
        agregar_tabla_por_formulario("EVALUACIONES - NIVEL JERÁRQUICO (FORMULARIO 1)", ["1"])
        agregar_tabla_por_formulario("EVALUACIONES - NIVELES MEDIO (FORMULARIOS 2, 3 y 4)", ["2", "3", "4"])
        agregar_tabla_por_formulario("EVALUACIONES - NIVELES OPERATIVOS (FORMULARIOS 5 Y 6)", ["5", "6"])
    
        return doc

    if st.button("📥 Generar y descargar informe Word"):
        if df_no_anuladas.empty:
            st.warning("⚠️ No hay evaluaciones válidas para esta dependencia.")
        else:
            doc = generar_planilla_docx(df_no_anuladas, dependencia_filtro)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                doc.save(tmp.name)
                tmp.seek(0)
                st.download_button(
                    label="📄 Descargar informe",
                    data=tmp.read(),
                    file_name=f"informe_{dependencia_filtro.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )


    
    
    # Consultar si la funcionalidad de anulación está habilitada
    conf = supabase.table("configuracion").select("valor").eq("id", "anulacion_activa").execute().data
    anulacion_activa = conf[0]["valor"] if conf else True

    if anulacion_activa and not df_no_anuladas.empty:
        st.markdown("<h2 style='font-size:24px;'>🔄 Evaluaciones que pueden anularse:</h2>", unsafe_allow_html=True)

        # Asegurar columnas necesarias
        for col in ["Seleccionar", "calif_puntaje", "apellido_nombre", "formulario",
                    "Fecha_formateada", "id_evaluacion", "cuil", "calificacion", "puntaje_total", "agrupamiento", "nivel", "grado", "ingresante"]:
            if col not in df_no_anuladas.columns:
                if col == "Seleccionar":
                    df_no_anuladas["Seleccionar"] = False
                else:
                    df_no_anuladas[col] = ""

        # Calcular columna calif_puntaje por si acaso
        df_no_anuladas["calif_puntaje"] = df_no_anuladas.apply(
            lambda row: f"{row['calificacion']} ({row['puntaje_total']})"
            if row.get("calificacion") and row.get("puntaje_total") else "",
            axis=1
        )

        # Crear tabla simplificada para mostrar
        columnas_mostrar = [
            "Seleccionar", "apellido_nombre", "formulario",
            "calif_puntaje", "Fecha_formateada", "id_evaluacion"
        ]
        df_para_mostrar = df_no_anuladas[columnas_mostrar].rename(columns={
            "Seleccionar": "Seleccionar",
            "apellido_nombre": "Apellido y Nombres",
            "formulario": "Form.",
            "calif_puntaje": "Calificación/Puntaje",
            "Fecha_formateada": "Fecha",
            "id_evaluacion": "id_evaluacion"  # Oculta visualmente
        })

        seleccion = st.data_editor(
            df_para_mostrar,
            use_container_width=True,
            hide_index=True,
            disabled=["Apellido y Nombres", "Form.", "Calificación/Puntaje", "Fecha", "id_evaluacion"],
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn("Seleccionar"),
                "id_evaluacion": None  # ⛔ Oculta visualmente
            }
        )

        # Botón para anular
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
                        supabase.table("evaluaciones").update({"anulada": True}).eq("id_evaluacion", id_eval).execute()
                        if cuil_sel:
                            supabase.table("agentes").update({"evaluado_2024": False}).eq("cuil", cuil_sel).execute()
                st.success(f"✅ {len(ids_seleccionados)} evaluaciones anuladas.")
                time.sleep(2)
                st.rerun()

    
    # TABLA DE ANULADAS
    df_anuladas = df_eval[df_eval["anulada"] == True].copy()
    df_anuladas["Estado"] = "Anulada"
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
        st.markdown("<h2 style='font-size:24px;'>❌ Evaluaciones anuladas:</h2>", unsafe_allow_html=True)
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
