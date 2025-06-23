import streamlit as st
import pandas as pd
from pytz import timezone
import time

from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml import OxmlElement

from docx.oxml.ns import qn
import tempfile
from docx.shared import Cm 

# ---- Vista: Evaluaciones ----
def mostrar(supabase):
    #st.header("📋 Evaluaciones realizadas")
    st.markdown("<h2 style='font-size:26px;'>📋 Evaluaciones realizadas</h1>", unsafe_allow_html=True)
    
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
    with cols[0]: st.metric("👥 Total a Evaluar", total_asignados)
    with cols[1]: st.metric("✅ Evaluados", evaluados)
    with cols[2]: st.metric("📊 % Evaluación", f"{porcentaje:.1f}%")
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

    # Unir con datos de agentes si no están ya
    agentes_completos = supabase.table("agentes").select("*").in_("cuil", cuils_asignados).execute().data
    df_agentes = pd.DataFrame(agentes_completos)
    
    if not df_agentes.empty:
        df_no_anuladas = df_no_anuladas.merge(df_agentes[[
            "cuil", "agrupamiento", "nivel", "ingresante", "apellido_nombre"
        ]], on="cuil", how="left", suffixes=("", "_agente"))
    
    # Reasegurar columnas requeridas por el informe
    columnas_necesarias = [
        "cuil", "apellido_nombre", "calificacion", "puntaje_total", "formulario",
        "nivel", "agrupamiento", "ingresante"
    ]
    for col in columnas_necesarias:
        if col not in df_no_anuladas.columns:
            df_no_anuladas[col] = ""


    
    # ---- INDICADORES DE DISTRIBUCIÓN POR CALIFICACIÓN ----
    st.markdown("<h2 style='font-size:24px;'>📋 Calificaciones</h2>", unsafe_allow_html=True)
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
    
    # ---- CREAR calif_puntaje SIEMPRE ANTES DE USARLA EN LA TABLA ----
    if "calif_puntaje" not in df_no_anuladas.columns:
        df_no_anuladas["calif_puntaje"] = df_no_anuladas.apply(
            lambda row: f"{row['calificacion']} ({row['puntaje_total']})"
            if pd.notna(row.get("calificacion", None)) and pd.notna(row.get("puntaje_total", None))
            else "",
            axis=1
        )

        #st.subheader("📋 Uso de formularios")
     # ---- INDICADORES DE USO DE FORMULARIOS ----
    st.markdown("<h2 style='font-size:24px;'>📋 Niveles de Evaluación</h2>", unsafe_allow_html=True)
    form_labels = ["1", "2", "3", "4", "5", "6"]
    form_counts = {f: 0 for f in form_labels}
    if not df_no_anuladas.empty and "formulario" in df_no_anuladas.columns:
        df_no_anuladas["formulario"] = df_no_anuladas["formulario"].astype(str)
        formulario_counts = df_no_anuladas["formulario"].value_counts()
        for f in form_labels:
            form_counts[f] = formulario_counts.get(f, 0)
    
    cols = st.columns(len(form_labels))
    for i, f in enumerate(form_labels):
        cols[i].metric(f"Formulario {f}", form_counts[f])

    st.markdown("<br><br>", unsafe_allow_html=True)  # Espacio más grande

    # ---- TABLA DE EVALUACIONES REGISTRADAS ----
    st.markdown("<h2 style='font-size:24px;'>✅ Evaluaciones registradas:</h2>", unsafe_allow_html=True)
    #st.subheader("✅ Evaluaciones registradas:")
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


    def set_cell_style(cell, bold=True, bg_color="104f8e", font_color="FFFFFF"):
        para = cell.paragraphs[0]
        run = para.runs[0] if para.runs else para.add_run(" ")
        run.text = run.text if run.text.strip() else " "
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.font.bold = bold
        run.font.color.rgb = RGBColor.from_string(font_color.upper())
    
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), bg_color)
        tcPr.append(shd)
    
        para.alignment = 1  # Centrado
    
    # Preparar dataframe combinado para informe
    df_informe = df_agentes.copy()
    
    # Reasegurar columnas necesarias en df_agentes
    columnas_necesarias = ["cuil", "apellido_nombre", "nivel", "agrupamiento", "ingresante"]
    for col in columnas_necesarias:
        if col not in df_informe.columns:
            df_informe[col] = ""
    
    # Preparar las columnas necesarias en df_no_anuladas
    columnas_eval = ["cuil", "formulario", "calificacion", "puntaje_total"]
    for col in columnas_eval:
        if col not in df_no_anuladas.columns:
            df_no_anuladas[col] = ""
    
    # Unir evaluaciones a todos los agentes (para listados por formulario)
    df_evaluados = df_informe.merge(
        df_no_anuladas[columnas_eval], on="cuil", how="left"
    ).fillna("")
    
    def generar_informe_docx(df_base, df_eval, dependencia_nombre):
        doc = Document()
    
        # Márgenes 2 cm
        section = doc.sections[0]
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2)
        section.right_margin = Cm(2)
    
        # Fuente general
        doc.styles["Normal"].font.name = "Calibri"
        doc.styles["Normal"].font.size = Pt(10)
    
        # Títulos con estilo
        def titulo(texto):
            p = doc.add_paragraph()
            run = p.add_run(texto)
            run.font.name = "Calibri"
            run.font.size = Pt(10)
            run.font.bold = True
            run.font.color.rgb = RGBColor.from_string("104f8e")
    
        # Encabezado que se repite en cada página
        header = section.header
        p_header = header.paragraphs[0]
        
        # Borrar contenido previo si lo hubiera
        p_header.clear()
        
        run = p_header.add_run(
            "INSTITUTO NACIONAL DE ESTADISTICA Y CENSOS\n"
            "DIRECCIÓN DE CAPACITACIÓN Y CARRERA DE PERSONAL\n"
            "EVALUACIÓN DE DESEMPEÑO 2024"
        )
        
        # Formato del texto
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = RGBColor.from_string("104f8e")
        
        # Alineación centrada
        p_header.alignment = 1  # Centrado
        
        # Interlineado simple
        p_header.paragraph_format.line_spacing = Pt(12)  # Equivale a sencillo en Word (1.0)

    
        # AGRUPAMIENTO
        titulo("PERSONAL POR TIPO DE AGRUPAMIENTO")
        gral = len(df_base[df_base["agrupamiento"] == "GRAL"])
        prof = len(df_base[df_base["agrupamiento"] == "PROF"])
        tabla_agrup = doc.add_table(rows=2, cols=2)
        tabla_agrup.style = 'Table Grid'
        for i, h in enumerate(["GENERAL", "PROFESIONAL"]):
            tabla_agrup.cell(0, i).text = h
            set_cell_style(tabla_agrup.cell(0, i))
            tabla_agrup.cell(1, i).text = str([gral, prof][i])
            set_cell_style(tabla_agrup.cell(1, i), bold=False)  # <-- centrado sin negrita
        
        # ESCALAFÓN
        titulo("PERSONAL POR TIPO DE NIVEL ESCALAFONARIO")
        niveles = ["A", "B", "C", "D", "E"]
        conteo_niveles = df_base["nivel"].value_counts()
        tabla_nivel = doc.add_table(rows=2, cols=5)
        tabla_nivel.style = 'Table Grid'
        for i, nivel in enumerate(niveles):
            tabla_nivel.cell(0, i).text = nivel
            set_cell_style(tabla_nivel.cell(0, i))
            tabla_nivel.cell(1, i).text = str(conteo_niveles.get(nivel, 0))
            set_cell_style(tabla_nivel.cell(1, i), bold=False)
        
        # EVALUADO / INGRESANTE
        titulo("PERSONAL EVALUADO")
        df_evaluable = df_base[df_base["ingresante"].isin([True, False])]
        no_ingresantes = len(df_evaluable[df_evaluable["ingresante"] == False])
        ingresantes = len(df_evaluable[df_evaluable["ingresante"] == True])
        total_evaluable = no_ingresantes + ingresantes
        evaluados = df_eval["calificacion"].apply(lambda x: x != "").sum()
        
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
            tabla_eval.cell(1, i).text = str([no_ingresantes, ingresantes, total_evaluable, evaluados][i])
            set_cell_style(tabla_eval.cell(1, i), bold=False)
    
        # FUNCION AUXILIAR PARA LISTADOS POR FORMULARIO
        def agregar_tabla_por_formulario(titulo_texto, formularios):
            titulo(titulo_texto)
            subset = df_eval[df_eval["formulario"].astype(str).isin(formularios)].sort_values("apellido_nombre")
    
            tabla = doc.add_table(rows=1, cols=3)
            tabla.style = 'Table Grid'
            for i, col in enumerate(["APELLIDOS Y NOMBRES", "CALIFICACIÓN", "PUNTAJE"]):
                tabla.cell(0, i).text = col
                set_cell_style(tabla.cell(0, i))
    
            if subset.empty:
                p = doc.add_paragraph("No hay evaluaciones registradas en este nivel.")
                p.paragraph_format.space_before = Pt(4)
                return
    
            for _, row in subset.iterrows():
                r = tabla.add_row().cells
                r[0].text = row.get("apellido_nombre", "")
                r[1].text = row.get("calificacion", "")
                puntaje = row.get("puntaje_total", "")
                try:
                    puntaje_float = float(puntaje)
                    puntaje = int(puntaje_float) if puntaje_float.is_integer() else puntaje_float
                except:
                    pass
                r[2].text = str(puntaje)
    
        agregar_tabla_por_formulario("EVALUACIONES - NIVEL JERÁRQUICO (FORMULARIO 1)", ["1"])
        agregar_tabla_por_formulario("EVALUACIONES - NIVELES MEDIO (FORMULARIOS 2, 3 y 4)", ["2", "3", "4"])
        agregar_tabla_por_formulario("EVALUACIONES - NIVELES OPERATIVOS (FORMULARIOS 5 Y 6)", ["5", "6"])
    
        return doc

    df_informe = df_agentes.copy()

    df_evaluados = df_informe.merge(
        df_no_anuladas[["cuil", "formulario", "calificacion", "puntaje_total", "apellido_nombre"]],
        on="cuil", how="left"
    ).fillna("")


    st.markdown("---")
    st.markdown("<h3 style='font-size:22px;'>📄 Generar y descargar informe resumen Word</h3>", unsafe_allow_html=True)
    
    if st.button("📥 Generar y Descargar Informe Word"):
        if df_informe.empty:
            st.warning("⚠️ No hay agentes registrados en esta unidad.")
        else:
            # Asegurar columnas necesarias en df_evaluados
            for col in ["formulario", "calificacion", "puntaje_total", "apellido_nombre"]:
                if col not in df_evaluados.columns:
                    df_evaluados[col] = ""
    
            with st.spinner("✏️ Generando documento..."):
                doc = generar_informe_docx(df_informe, df_evaluados, dependencia_filtro)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                    doc.save(tmp.name)
                    tmp_path = tmp.name  # Guardamos ruta temporal
    
            # Botón de descarga fuera del spinner
            with open(tmp_path, "rb") as file:
                st.download_button(
                    label="📄 Descargar Informe Word",
                    data=file,
                    file_name=f"informe_{dependencia_filtro.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

    


    if not df_no_anuladas.empty:
        st.markdown("<h2 style='font-size:24px;'>🔄 Evaluaciones que pueden anularse:</h2>", unsafe_allow_html=True)
      # st.subheader("🔄 Evaluaciones que pueden anularse:")
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

        #st.subheader("❌ Evaluaciones ya anuladas:")
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
