import streamlit as st
import pandas as pd
import io
import os
import math
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# —————————— Funciones auxiliares para Word ——————————

def generar_informe_comite_docx(df, unidad_nombre, total, cupo30, resumen_niveles, path_docx):
    """
    Anexo I – Informe para el Comité:
    - Fila 0 mergeada y sombreada con 'Unidad de Evaluación'
    - Fila 1: headers de columna
    - Filas de datos + TOTAL y Cupo 30%
    - Cuadro Resumen debajo
    """
    doc = Document()
    doc.add_heading("Anexo I – Informe para el Comité", level=1)

    # Tabla principal
    n_cols = 7
    n_rows = 1 + 1 + len(df) + 2
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.style = "Table Grid"

    # Fila 0: merge + sombreado gris
    cells0 = table.rows[0].cells
    cells0[0].text = f"Unidad de Evaluación: {unidad_nombre}"
    for c in cells0[1:]:
        cells0[0]._tc.merge(c._tc)
    tcPr = cells0[0]._tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd'); shd.set(qn('w:fill'), "BFBFBF"); tcPr.append(shd)
    cells0[0].paragraphs[0].alignment = 1

    # Fila 1: headers
    headers = ["Apellido y Nombre","CUIL","Nivel","Puntaje Absoluto",
               "Puntaje Relativo","Calificación","Formulario GEDO Nº"]
    for j, h in enumerate(headers):
        run = table.rows[1].cells[j].paragraphs[0].add_run(h)
        run.bold = True

    # Filas de datos
    for i, row in enumerate(df.itertuples(index=False), start=2):
        cells = table.rows[i].cells
        cells[0].text = row.apellido_nombre
        cells[1].text = str(row.cuil)
        cells[2].text = str(row.nivel)
        cells[3].text = str(row.puntaje_total)
        cells[4].text = f"{row.puntaje_relativo:.2f}"
        cells[5].text = row.calificacion
        cells[6].text = str(row.formulario)

    # TOTAL de agentes
    idx_tot = 2 + len(df)
    cells_tot = table.rows[idx_tot].cells
    cells_tot[2].text = "TOTAL de agentes"
    cells_tot[3].text = str(total)

    # Cupo Destacados (30%)
    cells_cupo = table.rows[idx_tot + 1].cells
    cells_cupo[2].text = "Cupo Destacados (30%)"
    cells_cupo[3].text = str(cupo30)

    # Cuadro Resumen
    doc.add_paragraph("")
    doc.add_heading("CUADRO RESUMEN", level=2)

    nivs   = list(resumen_niveles.columns)
    filas2 = list(resumen_niveles.index)
    tbl2   = doc.add_table(rows=len(filas2) + 1, cols=len(nivs) + 1)
    tbl2.style = "Table Grid"
    hdr2 = tbl2.rows[0].cells
    hdr2[0].text = "Nivel"
    for j, nv in enumerate(nivs, start=1):
        hdr2[j].text = str(nv)
    for i, fila in enumerate(filas2, start=1):
        cells = tbl2.rows[i].cells
        cells[0].text = fila
        for j, nv in enumerate(nivs, start=1):
            cells[j].text = str(resumen_niveles.loc[fila, nv])

    doc.save(path_docx)


def generar_anexo_ii_modelo_docx(df, unidad_analisis, unidad_evaluacion, path_docx):
    """
    Anexo II – MODELO LISTADO DE APOYO:
    - Título azul
    - Cabeceras grises: Unidad de Análisis / Evaluación
    - Tabla detalle + TOTAL + Bonif. correspondientes
    - Cuadro Resumen 1–6 + TOTAL
    - Nota al pie en cursiva
    """
    doc = Document()

    # Título azul
    p_tit = doc.add_paragraph()
    run   = p_tit.add_run("ANEXO II: MODELO LISTADO DE APOYO")
    run.font.color.rgb = RGBColor(0x00,0xA0,0xFF)
    run.bold = True

    # Cabeceras grises
    tbl_h = doc.add_table(rows=2, cols=1)
    tbl_h.style = "Table Grid"
    c0 = tbl_h.rows[0].cells[0]
    c0.text = f"UNIDAD DE ANÁLISIS: {unidad_analisis}"
    tcPr = c0._tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd'); shd.set(qn('w:fill'), "BFBFBF"); tcPr.append(shd)
    tbl_h.rows[1].cells[0].text = f"Unidad de Evaluación: {unidad_evaluacion}"

    doc.add_paragraph("")

    # Tabla detalle
    cols = ["Apellido y Nombre","Nº de CUIL","Nivel de Evaluación","Puntaje","Calificación"]
    n    = len(df)
    tbl  = doc.add_table(rows=1 + n + 2, cols=len(cols))
    tbl.style = "Table Grid"
    for j, h in enumerate(cols):
        tbl.rows[0].cells[j].text = h

    for i, row in enumerate(df.itertuples(index=False), start=1):
        c = tbl.rows[i].cells
        c[0].text = row.apellido_nombre
        c[1].text = str(row.cuil)
        c[2].text = str(row.formulario)
        c[3].text = str(row.puntaje_total)
        c[4].text = row.calificacion

    # TOTAL y Bonif.
    tbl.rows[n+1].cells[2].text = "TOTAL"
    tbl.rows[n+1].cells[3].text = str(n)
    tbl.rows[n+2].cells[2].text = "BONIF. CORRESPONDIENTES"
    tbl.rows[n+2].cells[3].text = str(math.floor(n * 0.3))

    # Cuadro Resumen
    doc.add_paragraph("")
    doc.add_heading("CUADRO RESUMEN", level=2)
    df["nivel_int"] = df["formulario"].astype(int)
    #tot_n = df.groupby("nivel_int")["cuil"].count().reindex(range(1,7), 0)
    tot_n = df.groupby("nivel_int")["cuil"].count().reindex(range(1,7), fill_value=0)

 
    dest_n = (df[df["calificacion"].str.upper()=="DESTACADO"]
                .groupby("nivel_int")["cuil"].count()
                .reindex(range(1,7), fill_value=0))
    corr_n= (tot_n * 0.3).apply(math.floor)
    diff_n= dest_n - corr_n
    sums = [tot_n.sum(), dest_n.sum(), corr_n.sum(), diff_n.sum()]
    niveles = list(range(1,7)) + ["TOTAL"]
    resumen = pd.DataFrame({
        "Cantidad de agentes":     list(tot_n.values) + [sums[0]],
        "Bonif. otorgadas":        list(dest_n.values)  + [sums[1]],
        "Bonif. correspondientes": list(corr_n.values) + [sums[2]],
        "Diferencia":              list(diff_n.values) + [sums[3]],
    }, index=niveles).T

    tbl2 = doc.add_table(rows=resumen.shape[0]+1, cols=resumen.shape[1]+1)
    tbl2.style = "Table Grid"
    hdr2 = tbl2.rows[0].cells
    hdr2[0].text = "Nivel"
    for j, nv in enumerate(resumen.columns, start=1):
        hdr2[j].text = str(nv)
    for i, fila in enumerate(resumen.index, start=1):
        cells = tbl2.rows[i].cells
        cells[0].text = fila
        for j, nv in enumerate(resumen.columns, start=1):
            cells[j].text = str(resumen.loc[fila, nv])

    # Nota en cursiva
    max_p = df["puntaje_total"].max()
    cand  = df[df["puntaje_total"]==max_p]["apellido_nombre"].tolist()
    nota  = (f"*El titular de la UA seleccionará un agente entre {', '.join(cand)} "
             f"con puntaje {max_p} (DESTACADO).")
    p_n = doc.add_paragraph(nota); p_n.italic = True

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
    st.markdown("<h1 style='font-size:24px;'>📋 Listado General y Análisis de Tramos</h1>", unsafe_allow_html=True)

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
    st.markdown(f"#### 🗂 Resumen por Formulario — {seleccion}")
    st.dataframe(res_for, use_container_width=True)

    # 6) Análisis detallado por UA
    regs=[] 
    for ua, grp in df_fil.groupby("unidad_analisis"):
        tot=len(grp)
        dest=grp[grp["calificacion"].str.upper()=="DESTACADO"]
        n_dest=len(dest)
        pct=round(n_dest/tot*100,2) if tot else 0
        c30=math.floor(tot*0.3); c10=math.floor(tot*0.1)
        ords=dest.sort_values("puntaje_relativo",ascending=False)["cuil"].astype(str).tolist()
        regs.append({"unidad_analisis":ua,"Evaluados":tot,"Destacados":n_dest,
                     "% Destacados":pct,"Cupo 30%":c30,"Cupo 10%":c10,
                     "Bonificados":len(ords[:c10]),
                     "Fecha Análisis":datetime.now().isoformat(),
                     "List CUIL Bonif.":"; ".join(ords[:c10]),
                     "Orden Puntaje":"; ".join(ords)})
    df_det=pd.DataFrame(regs)
    st.markdown(f"#### 🔍 Análisis por Unidad de Análisis — {seleccion}")
    st.dataframe(df_det, use_container_width=True)

    # PREPARAR datos para Anexos I & II
    df_inf = df_fil.sort_values("puntaje_total", ascending=False).copy()
    df_inf["nivel"]  = df_inf["formulario"].astype(int)
    df_inf = df_inf[["apellido_nombre","cuil","nivel","puntaje_total","puntaje_relativo","calificacion","formulario"]]
    total  = len(df_inf)
    cupo30 = math.floor(total*0.3)
    resumen_niveles = (df_inf.groupby("nivel")
                       .agg(Cantidad_de_agentes=("cuil","count"),
                            Bonif_otorgadas=("calificacion", lambda x:(pd.Series(x).str.upper()=="DESTACADO").sum()))
                       .reindex([1,2,3,4,5,6],fill_value=0))
    resumen_niveles["Bonif. correspondientes"] = (resumen_niveles["Cantidad_de_agentes"]*0.3).apply(math.floor)
    resumen_niveles["Diferencia"]              = resumen_niveles["Bonif_otorgadas"] - resumen_niveles["Bonif. correspondientes"]
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
