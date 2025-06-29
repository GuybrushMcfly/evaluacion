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
from streamlit_option_menu import option_menu

# ---- Vista: Evaluaciones ----
def mostrar(supabase):
    #st.header("📋 Evaluaciones realizadas")
    st.markdown("<h2 style='font-size:26px;'>📋 Evaluaciones realizadas</h2>", unsafe_allow_html=True)
    
    # Función para verificar rol activo
    def tiene_rol(*roles):
        return any(st.session_state.get("rol", {}).get(r, False) for r in roles)

    # Rol y dependencias desde sesión
    dependencia_usuario = st.session_state.get("dependencia", "")
    dependencia_general = st.session_state.get("dependencia_general", "")

    # Construir opciones de filtro de dependencia
    opciones_dependencia = []

    if tiene_rol("coordinador", "evaluador_general") and dependencia_general:
        opciones_dependencia.append(f"{dependencia_general} (todas)")

    if dependencia_usuario:
        opciones_dependencia.append(f"{dependencia_usuario} (individual)")

    dependencias_subordinadas = []
    if tiene_rol("coordinador", "evaluador_general") and dependencia_general:
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

    st.markdown("## ")
    
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

    if "calif_puntaje" not in df_no_anuladas.columns:
        df_no_anuladas["calif_puntaje"] = df_no_anuladas.apply(
            lambda row: f"{row['calificacion']} ({row['puntaje_total']})"
            if pd.notna(row.get("calificacion")) and pd.notna(row.get("puntaje_total"))
            else "",
            axis=1
        )
    
    # Unir con datos de agentes si no están ya
    agentes_completos = supabase.table("agentes").select("*").in_("cuil", cuils_asignados).execute().data
    df_agentes = pd.DataFrame(agentes_completos)
    
    if not df_agentes.empty:
        df_no_anuladas = df_no_anuladas.merge(df_agentes[[
            "cuil", "agrupamiento", "nivel", "ingresante", "apellido_nombre"
        ]], on="cuil", how="left", suffixes=("", "_agente"))
    
    # Menú horizontal de navegación
    seleccion = option_menu(
        menu_title=None,
        options=["📊 Indicadores", "✅ Evaluaciones"],
        icons=["bar-chart-line", "clipboard-check"],
        orientation="horizontal",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#f0f2f6"},
            "icon": {"color": "white", "font-size": "18px"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "center",
                "margin": "0px",
                "color": "white",
                "background-color": "#d32f2f",  # rojo inactivo
            },
            "nav-link-selected": {
                "background-color": "#b71c1c",  # rojo más oscuro
                "color": "white",
            },
        }

    )
    
    if seleccion == "📊 Indicadores":
        st.divider()
        st.markdown("<h2 style='font-size:24px;'>📊 Indicadores</h2>", unsafe_allow_html=True)
        cols = st.columns(3)
        with cols[0]: st.metric("👥 Total a Evaluar", total_asignados)
        with cols[1]: st.metric("✅ Evaluados", evaluados)
        with cols[2]: st.metric("📊 % Evaluación", f"{porcentaje:.1f}%")
        st.progress(min(100, int(porcentaje)), text=f"Progreso de evaluaciones registradas: {porcentaje:.1f}%")
    
        st.markdown("<h2 style='font-size:24px;'>🏅 Distribución por Calificación</h2>", unsafe_allow_html=True)
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
    

    
        st.markdown("<h2 style='font-size:24px;'>🗂️ Distribución por Nivel de Evaluación</h2>", unsafe_allow_html=True)
        df_no_anuladas["formulario"] = df_no_anuladas["formulario"].astype(str)
        niveles_eval = {
            "🔵 Nivel Jerárquico": ["1"],
            "🟣 Niveles Medios": ["2", "3", "4"],
            "🟢 Niveles Operativos": ["5", "6"]
        }
    
        cols = st.columns(3)
        for i, (titulo, formularios) in enumerate(niveles_eval.items()):
            cantidad = df_no_anuladas["formulario"].isin(formularios).sum()
            cols[i].metric(titulo, cantidad)
    
        columnas_necesarias = [
            "cuil", "apellido_nombre", "calificacion", "puntaje_total", "formulario",
            "nivel", "agrupamiento", "ingresante"
        ]
        for col in columnas_necesarias:
            if col not in df_no_anuladas.columns:
                df_no_anuladas[col] = ""
    
    elif seleccion == "✅ Evaluaciones":

   
  
    
        st.markdown("<br><br>", unsafe_allow_html=True)  # Espacio más grande
    
        # Asegurar columnas necesarias antes de usar la tabla
        for col in ["apellido_nombre", "formulario", "calif_puntaje", "evaluador", "Fecha_formateada"]:
            if col not in df_no_anuladas.columns:
                df_no_anuladas[col] = ""
        
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

        def set_cell_style(cell, bold=True, bg_color=None, font_color="000000"):
            para = cell.paragraphs[0]
            run = para.runs[0] if para.runs else para.add_run(" ")
            run.text = run.text if run.text.strip() else " "
            run.font.name = "Calibri"
            run.font.size = Pt(10)
            run.font.bold = bold
            run.font.color.rgb = RGBColor.from_string(font_color.upper())
        
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            if bg_color:
                shd = OxmlElement("w:shd")
                shd.set(qn("w:fill"), bg_color)
                tcPr.append(shd)
        
            para.alignment = 1  # Centrado
        
        
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
        
            # Encabezado
            header = section.header
            p_header = header.paragraphs[0]
            p_header.clear()
            run = p_header.add_run(
                f"INSTITUTO NACIONAL DE ESTADISTICA Y CENSOS\n"
                f"DIRECCIÓN DE CAPACITACIÓN Y CARRERA DE PERSONAL\n"
                f"EVALUACIÓN DE DESEMPEÑO 2024\n"
                f"UNIDAD DE ANÁLISIS: {dependencia_nombre}"
            )
            run.font.name = "Calibri"
            run.font.size = Pt(10)
            run.font.bold = True
            run.font.color.rgb = RGBColor.from_string("104f8e")
            p_header.alignment = 1
            p_header.paragraph_format.line_spacing = Pt(12)
    
    
            
            # AGRUPAMIENTO
            doc.add_paragraph()
    
            titulo("PERSONAL TOTAL POR TIPO DE AGRUPAMIENTO")
            gral = len(df_base[df_base["agrupamiento"] == "GRAL"])
            prof = len(df_base[df_base["agrupamiento"] == "PROF"])
            tabla_agrup = doc.add_table(rows=2, cols=2)
            tabla_agrup.style = 'Table Grid'
            for i, h in enumerate(["GENERAL", "PROFESIONAL"]):
                tabla_agrup.cell(0, i).text = h
                set_cell_style(tabla_agrup.cell(0, i), bg_color="104f8e", font_color="FFFFFF")
                tabla_agrup.cell(1, i).text = str([gral, prof][i])
                set_cell_style(tabla_agrup.cell(1, i), bold=False)
        
            doc.add_paragraph()
        
            # ESCALAFÓN
            titulo("PERSONAL TOTAL POR TIPO DE NIVEL ESCALAFONARIO")
            niveles = ["A", "B", "C", "D", "E"]
            conteo_niveles = df_base["nivel"].value_counts()
            tabla_nivel = doc.add_table(rows=2, cols=5)
            tabla_nivel.style = 'Table Grid'
            for i, nivel in enumerate(niveles):
                tabla_nivel.cell(0, i).text = nivel
                set_cell_style(tabla_nivel.cell(0, i), bg_color="104f8e", font_color="FFFFFF")
                tabla_nivel.cell(1, i).text = str(conteo_niveles.get(nivel, 0))
                set_cell_style(tabla_nivel.cell(1, i), bold=False)
        
            doc.add_paragraph()
        
            # EVALUADO / INGRESANTE
            titulo("PERSONAL PARA EVALUAR/EVALUADO")
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
                set_cell_style(tabla_eval.cell(0, i), bg_color="104f8e", font_color="FFFFFF")
                tabla_eval.cell(1, i).text = str([no_ingresantes, ingresantes, total_evaluable, evaluados][i])
                set_cell_style(tabla_eval.cell(1, i), bold=False)
        
            doc.add_paragraph()
        
            # FUNCION AUXILIAR: Listados por formulario
            def agregar_tabla_por_formulario(titulo_texto, formularios):
                titulo(titulo_texto)
                subset = df_eval[df_eval["formulario"].astype(str).isin(formularios)].sort_values("apellido_nombre")
        
                tabla = doc.add_table(rows=1, cols=3)
                tabla.style = 'Table Grid'
                headers = ["APELLIDOS Y NOMBRES", "CALIFICACIÓN", "PUNTAJE"]
                for i, col in enumerate(headers):
                    tabla.cell(0, i).text = col
                    set_cell_style(tabla.cell(0, i), bg_color="104f8e", font_color="FFFFFF")
        
                if subset.empty:
                    doc.add_paragraph("No hay evaluaciones registradas en este nivel.")
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
            doc.add_paragraph()
            agregar_tabla_por_formulario("EVALUACIONES - NIVELES MEDIO (FORMULARIOS 2, 3 y 4)", ["2", "3", "4"])
            doc.add_paragraph()
            agregar_tabla_por_formulario("EVALUACIONES - NIVELES OPERATIVOS (FORMULARIOS 5 Y 6)", ["5", "6"])
        
            return doc
    
        
       
        df_informe = df_agentes.copy()  # todos los agentes asignados
        
        df_evaluados = df_agentes[["cuil", "apellido_nombre"]].merge(
            df_no_anuladas[["cuil", "formulario", "calificacion", "puntaje_total"]],
            on="cuil", how="left"
        ).fillna("")
    
    
        st.markdown("---")
        st.markdown("<h3 style='font-size:22px;'>📋 Informe Evaluaciones Realizadas</h3>", unsafe_allow_html=True)
        
        if not df_informe.empty:
            for col in ["formulario", "calificacion", "puntaje_total", "apellido_nombre"]:
                if col not in df_evaluados.columns:
                    df_evaluados[col] = ""
        
            with st.spinner("✏️ Generando documento..."):
                doc = generar_informe_docx(df_informe, df_evaluados, dependencia_filtro)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                    doc.save(tmp.name)
                    tmp_path = tmp.name
        
            with open(tmp_path, "rb") as file:
                st.download_button(
                    label="📥 Descargar Informe",
                    data=file,
                    file_name=f"informe_{dependencia_filtro.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        else:
            st.warning("⚠️ No hay agentes registrados en esta unidad.")
    
    
        # Obtener configuración global
        config_items = supabase.table("configuracion").select("*").execute().data
        config_map = {item["id"]: item for item in config_items}
        anulacion_activa = config_map.get("anulacion_activa", {}).get("valor", True)
        
    
        # Mostrar bloque de anulaciones solo si está habilitado
        if not df_no_anuladas.empty and anulacion_activa:
            st.markdown("<h2 style='font-size:24px;'>🔄 Evaluaciones que pueden anularse:</h2>", unsafe_allow_html=True)
            df_no_anuladas["Seleccionar"] = False
            df_no_anuladas["calif_puntaje"] = df_no_anuladas.apply(
                lambda row: f"{row['calificacion']} ({row['puntaje_total']})", axis=1
            )
    
        
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
        elif not anulacion_activa:
            st.info("🔒 La anulación de evaluaciones está deshabilitada por configuración.")
    
        df_anuladas = df_eval[df_eval["anulada"] == True].copy()
        if not df_anuladas.empty:
            df_anuladas["calif_puntaje"] = df_anuladas.apply(
                lambda row: f"{row['calificacion']} ({row['puntaje_total']})", axis=1
            )
    
            #st.subheader("❌ Evaluaciones ya anuladas:")
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
