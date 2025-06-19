

import streamlit as st
import pandas as pd
import io
import os
import math
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def generar_informe_comite_docx(df, unidad_nombre, total, resumen_niveles, path_docx):
    """
    Genera el Anexo I – Informe para el Comité con:
    • Agrupaciones por Nivel (Unidad Residual, Niveles Medios, Niveles Operativos)
    • Listados detallados y mini-cuadros resumen por bloque
    • Totales Generales y Evaluables para Bonificación Especial
    • Resumen final por niveles
    """

    doc = Document()
    sec = doc.sections[0]
    # Márgenes en vertical (portrait)
    sec.top_margin    = Cm(2)
    sec.bottom_margin = Cm(2)
    sec.left_margin   = Cm(2)
    sec.right_margin  = Cm(2)

    # --- Encabezado ---
    header = sec.header
    p_head = header.paragraphs[0]
    p_head.text = "Evaluación de Desempeño 2024"
    p_head.alignment = 1
    for run in p_head.runs:
        run.font.name = "Calibri"
        run.font.color.rgb = RGBColor(0, 0, 0)

    # --- Título principal ---
    h1 = doc.add_heading("Resumen Evaluaciones", level=1)
    for run in h1.runs:
        run.font.name = "Calibri"
        run.font.color.rgb = RGBColor(0, 0, 0)

    # --- Título de la Unidad ---
    p_unit = doc.add_paragraph()
    run_u = p_unit.add_run(f"Unidad de Evaluación: {unidad_nombre}")
    run_u.bold = True
    run_u.font.name = "Calibri"
    run_u.font.color.rgb = RGBColor(0, 0, 0)

    azul = "B7E0F7"

    # --- Agrupar datos por reglas de BDD ---
    grupos = {}
    # Unidad Residual (Nivel 1)
    resid = df[df['nivel'] == 1]
    if not resid.empty:
        grupos['Unidad Residual'] = resid
    # Niveles Medios (2, 3, 4)
    medios = [2, 3, 4]
    if any(df[df['nivel'] == lvl].shape[0] < 6 for lvl in medios):
        grupos['Niveles Medios'] = df[df['nivel'].isin(medios)]
    else:
        for lvl in medios:
            tmp = df[df['nivel'] == lvl]
            if not tmp.empty:
                grupos[f'Nivel {lvl}'] = tmp
    # Niveles Operativos (5, 6)
    oper = [5, 6]
    if any(df[df['nivel'] == lvl].shape[0] < 6 for lvl in oper):
        grupos['Niveles Operativos'] = df[df['nivel'].isin(oper)]
    else:
        for lvl in oper:
            tmp = df[df['nivel'] == lvl]
            if not tmp.empty:
                grupos[f'Nivel {lvl}'] = tmp

    # --- Listados + mini-cuadros resumen por bloque ---
    cols = ["Apellido y Nombre", "CUIL", "Nivel", "Puntaje Absoluto", "Puntaje Relativo", "Calificación"]
    for titulo, tabla_df in grupos.items():
        # Sección
        h2 = doc.add_heading(titulo, level=2)
        for run in h2.runs:
            run.font.name = "Calibri"
            run.font.color.rgb = RGBColor(0, 0, 0)
        # Detalle
        tbl = doc.add_table(rows=1 + len(tabla_df), cols=len(cols), style="Table Grid")
        # Encabezados
        for j, c in enumerate(cols):
            cell = tbl.rows[0].cells[j]
            r = cell.paragraphs[0].add_run(c)
            r.bold = True
            r.font.name = "Calibri"
            tc = cell._tc.get_or_add_tcPr()
            shd = OxmlElement('w:shd'); shd.set(qn('w:val'), 'clear'); shd.set(qn('w:fill'), azul)
            tc.append(shd)
        # Filas
        for i, row in enumerate(tabla_df.itertuples(index=False), start=1):
            cells = tbl.rows[i].cells
            cells[0].text = row.apellido_nombre
            cells[1].text = str(row.cuil)
            cells[2].text = str(row.nivel)
            cells[3].text = str(row.puntaje_total)
            cells[4].text = f"{row.puntaje_relativo:.2f}"
            cells[5].text = row.calificacion
            for cell in cells:
                for p in cell.paragraphs:
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after  = Pt(0)
                    for run in p.runs:
                        run.font.name = 'Calibri'
                        run.font.size = Pt(9)
                        run.font.color.rgb = RGBColor(0, 0, 0)
        # Mini-cuadro resumen
        n = len(tabla_df)
        cupo = max(1, math.ceil(n * 0.1))
        tbl_sum = doc.add_table(rows=2, cols=2, style="Table Grid")
        tbl_sum.rows[0].cells[0].text = "Total evaluados"
        tbl_sum.rows[0].cells[1].text = str(n)
        tbl_sum.rows[1].cells[0].text = "BDD correspondientes (10%)"
        tbl_sum.rows[1].cells[1].text = str(cupo)
        # Formato
        for idx in (0, 1):
            c0 = tbl_sum.rows[idx].cells[0]
            tc0 = c0._tc.get_or_add_tcPr()
            sh = OxmlElement('w:shd'); sh.set(qn('w:val'), 'clear'); sh.set(qn('w:fill'), azul)
            tc0.append(sh)
            for p in c0.paragraphs:
                for run in p.runs:
                    run.bold = True
                    run.font.name = "Calibri"
                    run.font.size = Pt(9)
            for p in tbl_sum.rows[idx].cells[1].paragraphs:
                for run in p.runs:
                    run.font.name = "Calibri"
                    run.font.size = Pt(9)
        doc.add_paragraph("")

    # --- Salto de página antes de totales globales ---
    doc.add_page_break()

    # --- Totales Generales ---
    h2_tot = doc.add_heading("Totales Generales", level=2)
    for run in h2_tot.runs:
        run.font.name = "Calibri"
        run.font.color.rgb = RGBColor(0, 0, 0)
    cupo30 = max(1, math.ceil(total * 0.3))
    cupo10 = max(1, math.ceil(total * 0.1))
    tbl_tot = doc.add_table(rows=3, cols=2, style="Table Grid")
    labels = [
        ("TOTAL DE AGENTES EVALUADOS", str(total)),
        ("CUPO DESTACADOS (30%)", str(cupo30)),
        ("CUPO BONIFICACIÓN ESPECIAL (10%)", str(cupo10)),
    ]
    for idx, (lab, val) in enumerate(labels):
        c0 = tbl_tot.rows[idx].cells[0]
        c1 = tbl_tot.rows[idx].cells[1]
        c0.text = lab
        c1.text = val
        tc0 = c0._tc.get_or_add_tcPr()
        sh0 = OxmlElement('w:shd'); sh0.set(qn('w:val'), 'clear'); sh0.set(qn('w:fill'), azul)
        tc0.append(sh0)
        for p in c0.paragraphs:
            for run in p.runs:
                run.bold = True
                run.font.name = "Calibri"
                run.font.size = Pt(9)
        for p in c1.paragraphs:
            for run in p.runs:
                run.font.name = "Calibri"
                run.font.size = Pt(9)

    # --- Evaluables para Bonificación Especial ---
    h2_ev = doc.add_heading("Evaluables para Bonificación Especial", level=2)
    for run in h2_ev.runs:
        run.font.name = "Calibri"
        run.font.color.rgb = RGBColor(0, 0, 0)
    max_rel = df[df["calificacion"].str.upper() == "DESTACADO"]["puntaje_relativo"].max()
    evaluables = df[(df["calificacion"].str.upper() == "DESTACADO") & (df["puntaje_relativo"] == max_rel)]
    cols_ev = ["Apellido y Nombre", "Calificación", "Puntaje Absoluto", "Puntaje Relativo", "Bonificado"]
    tbl_ev = doc.add_table(rows=1 + len(evaluables), cols=len(cols_ev), style="Table Grid")
    for j, h in enumerate(cols_ev):
        cell = tbl_ev.rows[0].cells[j]
        cell.text = h
        tc = cell._tc.get_or_add_tcPr()
        sh0 = OxmlElement('w:shd'); sh0.set(qn('w:val'), 'clear'); sh0.set(qn('w:fill'), azul)
        tc.append(sh0)
        for run in cell.paragraphs[0].runs:
            run.font.name = "Calibri"
            run.bold = True
    for i, row in enumerate(evaluables.itertuples(index=False), start=1):
        cells = tbl_ev.rows[i].cells
        cells[0].text = row.apellido_nombre
        cells[1].text = row.calificacion
        cells[2].text = str(row.puntaje_total)
        cells[3].text = f"{row.puntaje_relativo:.2f}"
        cells[4].text = "SI" if hasattr(row, "bonificacion_especial") and row.bonificacion_especial else ""
        for cell in cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.name = 'Calibri'
                    run.font.size = Pt(9)

    # --- Resumen por Niveles ---
    h2_res = doc.add_heading("Resumen por Niveles de Evaluación", level=2)
    for run in h2_res.runs:
        run.font.name = "Calibri"
        run.font.color.rgb = RGBColor(0, 0, 0)
    nivs = list(resumen_niveles.columns)
    filas = list(resumen_niveles.index)
    tbl2 = doc.add_table(rows=1 + len(filas), cols=1 + len(nivs), style="Table Grid")
    hdr = tbl2.rows[0].cells
    hdr[0].text = "Nivel"
    for j, nv in enumerate(nivs, start=1):
        hdr[j].text = str(nv)
    for i, fila in enumerate(filas, start=1):
        rc = tbl2.rows[i].cells
        rc[0].text = str(fila)
        for j, nv in enumerate(nivs, start=1):
            rc[j].text = str(resumen_niveles.loc[fila, nv])

    # --- Pie de página ---
    footer = sec.footer.paragraphs[0]
    footer.clear()
    left = footer.add_run("DIRECCIÓN DE CAPACITACIÓN Y CARRERA DEL PERSONAL")
    left.font.name = "Calibri"
    footer.add_run("\t")
    fecha = datetime.today().strftime("%d/%m/%Y")
    runp = footer.add_run(f"{fecha}  Página ")
    runp.font.name = "Calibri"
    fld = OxmlElement('w:fldSimple'); fld.set(qn('w:instr'), 'PAGE'); runp._r.append(fld)
    footer.add_run(" de ")
    fld2 = OxmlElement('w:fldSimple'); fld2.set(qn('w:instr'), 'NUMPAGES'); footer.runs[-1]._r.append(fld2)
    footer.paragraph_format.alignment = 0

    doc.save(path_docx)



def generar_anexo_iii_docx(texto, path_docx):
    doc = Document()
    doc.add_heading("ANEXO III - ACTA DE VEEDURÍA GREMIAL", level=1)
    doc.add_paragraph(texto.strip())
    doc.save(path_docx)


def generar_cuadro_resumen_docx(df_resumen, path_docx):
    doc = Document()
    doc.add_heading("Cuadro Resumen de Niveles", level=1)
    niveles = list(df_resumen.columns)
    filas   = list(df_resumen.index)
    table   = doc.add_table(rows=len(filas)+1, cols=len(niveles)+1)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Nivel"
    for j, nivel in enumerate(niveles, start=1):
        table.rows[0].cells[j].text = str(nivel)
    for i, fila in enumerate(filas, start=1):
        cells = table.rows[i].cells
        cells[0].text = fila
        for j, nivel in enumerate(niveles, start=1):
            cells[j].text = str(df_resumen.loc[fila, nivel])
    doc.save(path_docx)

# --- NUEVA FUNCIÓN DE ANÁLISIS AUTOMÁTICO ---
def analizar_evaluaciones(df):
    df = df.copy()
    df["residual"] = False
    df["nivel"] = df["formulario"].astype(int)

    # Nivel 1: siempre residual
    df.loc[df["nivel"] == 1, "residual"] = True

    # Niveles medios y operativos: agrupar por unidad_analisis y marcar si hay <6
    for nivel_rango in [(2, 3, 4), (5, 6)]:
        df_tmp = df[df["nivel"].isin(nivel_rango)]
        conteo = df_tmp.groupby("unidad_analisis")["cuil"].count()
        residuales = conteo[conteo < 6].index
        df.loc[df["unidad_analisis"].isin(residuales) & df["nivel"].isin(nivel_rango), "residual"] = True

    return df[["id_evaluacion", "residual"]]



def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>📋 Análisis de Evaluaciones</h1>", unsafe_allow_html=True)

    # 1) Carga
    evals   = supabase.table("evaluaciones").select("*").execute().data or []
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data or []
    unids   = supabase.table("unidades_evaluacion").select("*").execute().data or []
    if not evals or not unids:
        st.warning("No hay datos.")
        return

    # 2) Filtrar y mapear
    evals = [e for e in evals if not e.get("anulada") and e.get("activo")]
    mapa  = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    # 3) Listado general + Excel
    filas = [{
        "CUIL": str(e["cuil"]),
        "AGENTE": mapa.get(e["cuil"], "Desconocido"),
        "FORMULARIO": e.get("formulario",""),
        "CALIFICACIÓN": e.get("calificacion",""),
        "PUNTAJE TOTAL": e.get("puntaje_total") or 0,
        "DEPENDENCIA GENERAL": e.get("dependencia_general","")
    } for e in evals]
    df_gen = pd.DataFrame(filas)
    st.markdown("#### 📑 Listado General de Evaluaciones")
    st.dataframe(df_gen, use_container_width=True)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df_gen.to_excel(w, index=False, sheet_name="Evaluaciones")
    buf.seek(0)
    st.download_button("📥 Descargar Listado General (Excel)", buf, "listado_general.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # 4) Botón para análisis automático
    if st.button("⚙️ Realizar Análisis de Residuales"):
        df_ev = pd.DataFrame(evals)
        df_actualizados = analizar_evaluaciones(df_ev)
        for i, row in df_actualizados.iterrows():
            supabase.table("evaluaciones").update({"residual": row["residual"]}).eq("id_evaluacion", row["id_evaluacion"]).execute()
        st.success("✅ Análisis realizado. Evaluaciones actualizadas.")

    # 5) Filtro por DG y Residual General
    df_ev = pd.DataFrame(supabase.table("evaluaciones").select("*").execute().data)
    df_un = pd.DataFrame(unids)
    df_ev["residual_general"] = df_ev["residual"] == True
    opciones = sorted(df_ev["dependencia_general"].dropna().unique().tolist())
    if df_ev["residual_general"].any():
        opciones.append("RESIDUAL GENERAL")
    opciones.append("TODAS")

    seleccion = st.selectbox("Seleccioná una Dirección General", opciones)

    if seleccion == "RESIDUAL GENERAL":
        df_fil = df_ev[df_ev["residual_general"] == True]
    elif seleccion == "TODAS":
        df_fil = df_ev
    else:
        df_fil = df_ev[df_ev["dependencia_general"] == seleccion]

    if df_fil.empty:
        st.info("No hay evaluaciones para mostrar.")
        return

    # PREPARAR datos para Anexos I & II
    df_inf = df_fil.sort_values("puntaje_total", ascending=False).copy()
    df_inf["nivel"] = df_inf["formulario"].astype(int)

    # Si tu tabla evaluaciones tiene "agrupamiento" y "tramo", incluí esas columnas acá:
    df_inf = df_inf[["apellido_nombre", "cuil", "nivel", "puntaje_total", "puntaje_relativo",
                     "calificacion", "formulario", "agrupamiento", "tramo"]]
    total  = len(df_inf)
    cupo30 = math.floor(total*0.3)
    resumen_niveles = (df_inf.groupby("nivel")
                   .agg(Cantidad_de_agentes=("cuil","count"),
                        Bonif_otorgadas=("calificacion", lambda x:(pd.Series(x).str.upper()=="DESTACADO").sum()))
                   .reindex([1,2,3,4,5,6], fill_value=0))

    resumen_niveles["Bonif. correspondientes"] = (
        resumen_niveles["Cantidad_de_agentes"] * 0.3
    ).round().astype(int)

    resumen_niveles["Diferencia"] = (
        resumen_niveles["Bonif_otorgadas"] - resumen_niveles["Bonif. correspondientes"]
    )
    resumen_niveles["Diferencia"] = resumen_niveles["Diferencia"].apply(
        lambda x: f"{x:+d}" if x != 0 else "0"
    )

    df_res = pd.DataFrame({
        "Cantidad de agentes":     resumen_niveles["Cantidad_de_agentes"],
        "Bonif. otorgadas":        resumen_niveles["Bonif_otorgadas"],
        "Bonif. correspondientes": resumen_niveles["Bonif. correspondientes"],
        "Diferencia":              resumen_niveles["Diferencia"]
    }).T

    df_modelo = df_inf[["apellido_nombre","cuil","formulario","puntaje_total","calificacion"]]

    # 7) Anexo I
    if st.button("📄 Generar Anexo I – Informe para el Comité"):
        os.makedirs("tmp_anexos", exist_ok=True)
        path1="tmp_anexos/anexo_I_informe_comite.docx"
        generar_informe_comite_docx(df_inf, seleccion, total, df_res, path1)

        with open(path1,"rb") as f:
            st.download_button("📥 Descargar Anexo I", f, "anexo_I_informe_comite.docx")

    # 8) Cuadro Resumen de Niveles
    if st.button("📄 Generar Cuadro Resumen de Niveles"):
        os.makedirs("tmp_anexos", exist_ok=True)
        path2="tmp_anexos/cuadro_resumen_niveles.docx"
        generar_cuadro_resumen_docx(df_res, path2)
        with open(path2,"rb") as f:
            st.download_button("📥 Descargar Cuadro Resumen", f, "cuadro_resumen_niveles.docx")

    # 9) Anexo II – Modelo Listado de Apoyo
    if st.button("📄 Generar Anexo II – Modelo Listado de Apoyo"):
        os.makedirs("tmp_anexos", exist_ok=True)
        path3="tmp_anexos/anexo_ii_modelo.docx"
        generar_anexo_ii_modelo_docx(df_modelo, seleccion, seleccion, path3)
        with open(path3,"rb") as f:
            st.download_button("📥 Descargar Anexo II Modelo", f, "anexo_ii_modelo.docx")

    # 10) Anexo III – Acta de Veeduría
    if st.button("📄 Generar Anexo III"):
        tot=len(df_fil)
        dest=(df_fil["calificacion"].str.upper()=="DESTACADO").sum()
        acta = (f"ACTA DE VEEDURÍA GREMIAL\n\n"
                f"En la dependencia {seleccion}, con un total de {tot} personas evaluadas, "
                f"se asignó la bonificación por desempeño destacado a {dest} agentes, de acuerdo "
                f"al cupo máximo permitido del 30% según la normativa vigente.\n\n"
                "La veeduría gremial constató que el procedimiento se realizó conforme a la normativa, "
                "y se firmó en señal de conformidad.\n\n"
                "Fecha: ...........................................................\n\n"
                "Firmas:\n- Representante de la unidad de análisis\n- Veedor/a gremial")
        os.makedirs("tmp_anexos", exist_ok=True)
        path4="tmp_anexos/anexo_iii.docx"
        generar_anexo_iii_docx(acta, path4)
        with open(path4,"rb") as f:
            st.download_button("📥 Descargar Anexo III", f, "anexo_iii.docx")
