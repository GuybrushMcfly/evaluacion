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

def generar_informe_comite_docx(df, unidad_nombre, total, cupo30, resumen_niveles, path_docx):
    doc = Document()
    sec = doc.sections[0]
    # Apaisado (landscape)
    sec.orientation = 1  # 0=portrait, 1=landscape
    sec.page_width, sec.page_height = sec.page_height, sec.page_width
    # Márgenes
    sec.top_margin    = Cm(2.5)
    sec.bottom_margin = Cm(2)
    sec.left_margin   = Cm(2)
    sec.right_margin  = Cm(2)

    # ——— ENCABEZADO (HEADER) ———
    header = sec.header
    p_head = header.paragraphs[0]
    p_head.text = "Evaluación de Desempeño 2024"
    p_head.alignment = 1  # centrado
    for run in p_head.runs:
        run.font.name = "Calibri"

    # ——— TÍTULO ———
    h1 = doc.add_heading("Anexo I – Informe para el Comité", level=1)
    for run in h1.runs:
        run.font.name = "Calibri"

    # ——— TABLA PRINCIPAL ———
    n_cols = 7
    n_rows = 1 + 1 + len(df)
    table = doc.add_table(rows=n_rows, cols=n_cols, style="Table Grid")

    azul = "B7E0F7"
    # Header unificado
    hdr0 = table.rows[0].cells
    hdr0[0].text = f"Unidad de Evaluación: {unidad_nombre}"
    for cell in hdr0[1:]:
        hdr0[0]._tc.merge(cell._tc)
    tcPr = hdr0[0]._tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:fill'), azul)
    tcPr.append(shd)
    hdr0[0].paragraphs[0].alignment = 1
    for run in hdr0[0].paragraphs[0].runs:
        run.font.name = "Calibri"

    # Encabezados de tabla (azul clarito)
    headers = ["Apellido y Nombre","CUIL","Nivel","Puntaje Absoluto",
               "Puntaje Relativo","Calificación","Formulario GEDO Nº"]
    for j, h in enumerate(headers):
        run = table.rows[1].cells[j].paragraphs[0].add_run(h)
        run.bold = True
        run.font.name = "Calibri"
        # Fondo azul clarito
        tc = table.rows[1].cells[j]._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'),'clear')
        shd.set(qn('w:fill'),azul)
        tc.append(shd)

    # Filas de datos (blanco, Calibri 9)
    for i, row in enumerate(df.itertuples(index=False), start=2):
        cells = table.rows[i].cells
        cells[0].text = row.apellido_nombre
        cells[1].text = str(row.cuil)
        cells[2].text = str(row.nivel)
        cells[3].text = str(row.puntaje_total)
        cells[4].text = f"{row.puntaje_relativo:.2f}"
        cells[5].text = row.calificacion
        cells[6].text = str(row.formulario)
        for cell in cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after  = Pt(0)
                for run in p.runs:
                    run.font.name = 'Calibri'
                    run.font.size = Pt(9)

    # ——— SALTO DE PÁGINA ———
    doc.add_page_break()

    # ——— MINI-TABLA DE TOTALES ———
    # --- MINI-TABLA DE TOTALES ---
    h2 = doc.add_heading("Totales Generales", level=2)
    for run in h2.runs:
        run.font.name = "Calibri"

    cupo10 = max(1, round(total * 0.1))  # Siempre al menos 1 si hay más de 5
    tbl_tot = doc.add_table(rows=3, cols=2, style="Table Grid")
    azul = "B7E0F7"

    tot_labels = [
        ("TOTAL de agentes", str(total)),
        ("Cupo Destacados (30%)", str(round(cupo30))),
        ("CUPO BONIFICACIÓN ESPECIAL (10%)", str(cupo10)),
    ]
    for idx, (label, value) in enumerate(tot_labels):
        tbl_tot.rows[idx].cells[0].text = label
        tbl_tot.rows[idx].cells[1].text = value
        # Azul clarito de fondo a la fila completa
        for cell in tbl_tot.rows[idx].cells:
            tc = cell._tc.get_or_add_tcPr()
            sh = OxmlElement('w:shd')
            sh.set(qn('w:val'), 'clear')
            sh.set(qn('w:fill'), azul)
            tc.append(sh)
            for p in cell.paragraphs:
                p.alignment = 1
                for run in p.runs:
                    run.bold = True
                    run.font.name = "Calibri"
                    run.font.size = Pt(9)

    # --- MINI-TABLA DE EVALUABLES PARA BONIFICACIÓN ESPECIAL ---
    doc.add_paragraph("")  # Espacio
    h2b = doc.add_heading("Evaluables para Bonificación Especial", level=2)
    for run in h2b.runs:
        run.font.name = "Calibri"

    # Filtrar candidatos: DESTACADO, puntaje relativo más alto
    max_rel = df[df["calificacion"].str.upper() == "DESTACADO"]["puntaje_relativo"].max()
    evaluables = df[(df["calificacion"].str.upper() == "DESTACADO") & (df["puntaje_relativo"] == max_rel)]

    cols_ev = ["Apellido y Nombre", "Nivel", "Agrupamiento", "Tramo"]
    tbl_ev = doc.add_table(rows=1+len(evaluables), cols=4, style="Table Grid")
    azul = "B7E0F7"
    # Encabezado
    for j, h in enumerate(cols_ev):
        cell = tbl_ev.rows[0].cells[j]
        cell.text = h
        tc = cell._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:fill'), azul)
        tc.append(shd)
        for run in cell.paragraphs[0].runs:
            run.font.name = "Calibri"
            run.font.bold = True
    # Filas
    for i, row in enumerate(evaluables.itertuples(index=False), start=1):
        cells = tbl_ev.rows[i].cells
        cells[0].text = row.apellido_nombre
        cells[1].text = str(row.nivel)
        cells[2].text = getattr(row, "agrupamiento", "")
        cells[3].text = getattr(row, "tramo", "")
        for cell in cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.name = 'Calibri'
                    run.font.size = Pt(9)


    # Espacio antes del cuadro resumen
    doc.add_paragraph("")

    # ——— CUADRO RESUMEN ———
    h2b = doc.add_heading("CUADRO RESUMEN", level=2)
    for run in h2b.runs:
        run.font.name = "Calibri"
    nivs   = list(resumen_niveles.columns)
    filas2 = list(resumen_niveles.index)
    tbl2   = doc.add_table(rows=len(filas2)+1, cols=len(nivs)+1, style="Table Grid")
    hdr2   = tbl2.rows[0].cells
    hdr2[0].text = "Nivel"
    for j, nv in enumerate(nivs, start=1):
        hdr2[j].text = str(nv)
    for cell in hdr2:
        tc = cell._tc.get_or_add_tcPr()
        sh = OxmlElement('w:shd')
        sh.set(qn('w:val'),'clear')
        sh.set(qn('w:fill'),azul)
        tc.append(sh)
        for run in cell.paragraphs[0].runs:
            run.font.name = "Calibri"
    for i, fila in enumerate(filas2, start=1):
        rc = tbl2.rows[i].cells
        rc[0].text = fila
        for j, nivel in enumerate(nivs, start=1):
            rc[j].text = str(resumen_niveles.loc[fila, nivel])
        for cell in rc:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.name = 'Calibri'
                    run.font.size = Pt(9)

    # ——— PIE DE PÁGINA (FOOTER) ———
    footer = sec.footer
    p_foot = footer.paragraphs[0]
    p_foot.clear()
    # Izquierda
    left_run = p_foot.add_run("DIRECCIÓN DE CAPACITACIÓN Y CARRERA DEL PERSONAL")
    left_run.font.name = "Calibri"
    # Tabulación (para separar izq/derecha; Word lo interpreta en dos extremos si usás tabs)
    p_foot.add_run("\t")
    # Derecha: fecha, paginación
    fecha_hoy = datetime.today().strftime("%d/%m/%Y")
    right_run = p_foot.add_run(f"{fecha_hoy}  Página ")
    right_run.font.name = "Calibri"
    # Campo para número de página
    fldPage = OxmlElement('w:fldSimple'); fldPage.set(qn('w:instr'), 'PAGE')
    right_run._r.append(fldPage)
    p_foot.add_run(" de ")
    fldNumPages = OxmlElement('w:fldSimple'); fldNumPages.set(qn('w:instr'), 'NUMPAGES')
    p_foot.runs[-1]._r.append(fldNumPages)
    p_foot.alignment = 0  # izquierda

    doc.save(path_docx)



def generar_anexo_ii_modelo_docx(df, unidad_analisis, unidad_evaluacion, path_docx):
    """
    Anexo II – Modelo Listado de Apoyo con:
    • Márgenes: igual que Anexo I
    • Título azul
    • Cabeceras grises
    • Tabla detalle + zebra + totales (cupo30 redondeado)
    • Cuadro Resumen con signo Dif. (sólo si ≠ 0)
    • Nota al pie
    """
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin    = Cm(2.5)
    sec.bottom_margin = Cm(2)
    sec.left_margin   = Cm(2)
    sec.right_margin  = Cm(2)

    # Título azul
    p_tit = doc.add_paragraph()
    run   = p_tit.add_run("ANEXO II: MODELO LISTADO DE APOYO")
    run.font.color.rgb = RGBColor(0x00,0xA0,0xFF); run.bold = True

    # Cabeceras grises
    hdr = doc.add_table(rows=2, cols=1, style="Table Grid")
    c0  = hdr.rows[0].cells[0]
    c0.text = f"UNIDAD DE ANÁLISIS: {unidad_analisis}"
    tc0 = c0._tc.get_or_add_tcPr()
    s0  = OxmlElement('w:shd'); s0.set(qn('w:val'),'clear'); s0.set(qn('w:fill'),'BFBFBF'); tc0.append(s0)
    hdr.rows[1].cells[0].text = f"Unidad de Evaluación: {unidad_evaluacion}"

    doc.add_paragraph("")

    # Tabla detalle
    cols = ["Apellido y Nombre","Nº de CUIL","Nivel de Evaluación","Puntaje","Calificación"]
    n    = len(df)
    tbl  = doc.add_table(rows=1+n+2, cols=len(cols), style="Table Grid")
    for j, h in enumerate(cols):
        tbl.rows[0].cells[j].text = h
    for i, row in enumerate(df.itertuples(index=False), start=1):
        c = tbl.rows[i].cells
        c[0].text = row.apellido_nombre
        c[1].text = str(row.cuil)
        c[2].text = str(row.formulario)
        c[3].text = str(row.puntaje_total)
        c[4].text = row.calificacion

    # Zebra
    for idx, rw in enumerate(tbl.rows[1:1+n], start=0):
        if idx % 2 == 1:
            for cell in rw.cells:
                tc = cell._tc.get_or_add_tcPr()
                sd = OxmlElement('w:shd'); sd.set(qn('w:val'),'clear'); sd.set(qn('w:fill'),'F2F2F2'); tc.append(sd)

    # Totales
    tbl.rows[n+1].cells[2].text = "TOTAL"
    tbl.rows[n+1].cells[3].text = str(n)
    cup = round(n * 0.3)
    tbl.rows[n+2].cells[2].text = "BONIF. CORRESPONDIENTES"
    tbl.rows[n+2].cells[3].text = str(cup)

    # Espaciado + Calibri 9
    for rw in tbl.rows:
        for cell in rw.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after  = Pt(0)
                for run in p.runs:
                    run.font.name = 'Calibri'
                    run.font.size = Pt(9)

    # Cuadro Resumen con signo sólo si ≠ 0
    tot_n  = df.groupby(df["formulario"].astype(int))["cuil"].count().reindex(range(1,7), fill_value=0)
    dest_n = df[df["calificacion"].str.upper()=="DESTACADO"]\
                .groupby(df["formulario"].astype(int))["cuil"].count().reindex(range(1,7), fill_value=0)
    corr_n = (tot_n * 0.3).round().astype(int)
    diff_n = dest_n - corr_n

    niveles = list(range(1,7)) + ["TOTAL"]
    resumen = {
        "Cantidad de agentes":     list(tot_n.values)    + [tot_n.sum()],
        "Bonif. otorgadas":        list(dest_n.values)   + [dest_n.sum()],
        "Bonif. correspondientes": list(corr_n.values)   + [corr_n.sum()],
        "Diferencia":              [ (f"{x:+d}" if x!=0 else "0")
                                     for x in list(diff_n.values) + [diff_n.sum()] ]
    }
    df_res = pd.DataFrame(resumen, index=niveles).T

    doc.add_paragraph("")
    doc.add_heading("CUADRO RESUMEN", level=2)
    tbl2 = doc.add_table(rows=df_res.shape[0]+1, cols=df_res.shape[1]+1, style="Table Grid")
    hdr2 = tbl2.rows[0].cells
    hdr2[0].text = "Nivel"
    for j, nv in enumerate(df_res.columns, start=1):
        hdr2[j].text = str(nv)
    for cell in hdr2:
        tc = cell._tc.get_or_add_tcPr()
        sd = OxmlElement('w:shd'); sd.set(qn('w:val'),'clear'); sd.set(qn('w:fill'),'BFBFBF'); tc.append(sd)
    for i, fila in enumerate(df_res.index, start=1):
        c = tbl2.rows[i].cells
        c[0].text = fila
        for j, nv in enumerate(df_res.columns, start=1):
            c[j].text = str(df_res.loc[fila, nv])
        for p in c[0].paragraphs:
            for run in p.runs:
                run.font.name = 'Calibri'
                run.font.size = Pt(9)

    # Nota al pie
    max_p = df["puntaje_total"].max()
    cand  = df[df["puntaje_total"]==max_p]["apellido_nombre"].tolist()
    nota  = f"*El titular de la UA seleccionará un agente entre {', '.join(cand)} con puntaje {max_p} (DESTACADO)."
    doc.add_paragraph(nota).italic = True

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


# —————————— Streamlit ——————————

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

    # 4) Filtrado por DG / Residual
    df_ev = pd.DataFrame(evals)
    df_un = pd.DataFrame(unids)
    resid = df_un[df_un["residual"]]["unidad_analisis"].unique()
    df_ev["residual_general"] = df_ev["unidad_analisis"].isin(resid)
    opts = sorted(df_ev["dependencia_general"].dropna().unique()) + ["RESIDUAL GENERAL"]
    seleccion = st.selectbox("Seleccioná una Dirección General", opts)
    df_fil = df_ev[df_ev["residual_general"]] if seleccion=="RESIDUAL GENERAL" \
             else df_ev[df_ev["dependencia_general"]==seleccion]
    if df_fil.empty:
        st.info("No hay evaluaciones."); return

    # 5) Resumen por Formulario
    res_for = (df_fil.groupby("formulario")
               .agg(evaluados_total=("cuil","count"),
                    destacados_total=("calificacion", lambda x: (pd.Series(x).str.upper()=="DESTACADO").sum()))
               .reset_index())
    res_for["% Destacados"] = (res_for["destacados_total"]/res_for["evaluados_total"]*100).round(2)
    res_for["Cupo 30%"]     = (res_for["evaluados_total"]*0.3).round().astype(int)
    res_for["Cupo 10%"]     = (res_for["evaluados_total"]*0.1).round().astype(int)
    st.markdown(f"#### 🗂 Resumen por Formulario")
    st.dataframe(res_for, use_container_width=True)


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
        generar_informe_comite_docx(df_inf, seleccion, total, cupo30, df_res, path1)
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
