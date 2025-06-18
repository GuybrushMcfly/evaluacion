import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime
from docx import Document
from docx.shared import RGBColor, Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import math

# —————————— Funciones auxiliares para Word ——————————

def generar_anexo_ii_modelo_docx(df, unidad_analisis, unidad_evaluacion, path_docx):
    """
    Genera el Anexo II – MODELO LISTADO DE APOYO
    df debe tener columnas:
      ['apellido_nombre','cuil','formulario','puntaje_total','calificacion']
    unidad_analisis: texto del header gris superior
    unidad_evaluacion: texto del subheader gris
    """
    doc = Document()

    # 1) Título azul
    p_tit = doc.add_paragraph()
    run = p_tit.add_run("ANEXO II: MODELO LISTADO DE APOYO")
    run.font.color.rgb = RGBColor(0x00,0xA0,0xFF)
    run.bold = True

    # 2) Cabeceras grises
    tbl_h = doc.add_table(rows=2, cols=1)
    tbl_h.style = "Table Grid"
    cell1 = tbl_h.rows[0].cells[0]
    cell1.text = f"UNIDAD DE ANÁLISIS: {unidad_analisis}"
    # fondo gris
    tcPr = cell1._tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:fill'), "BFBFBF")
    tcPr.append(shd)
    tbl_h.rows[1].cells[0].text = f"Unidad de Evaluación: {unidad_evaluacion}"

    doc.add_paragraph("")  # espacio

    # 3) Tabla de detalle
    cols = ["Apellido y Nombre","Nº de CUIL","Nivel de Evaluación","Puntaje","Calificación"]
    n    = len(df)
    tbl  = doc.add_table(rows=1 + n + 2, cols=len(cols))
    tbl.style = "Table Grid"

    # encabezados
    for j, title in enumerate(cols):
        tbl.rows[0].cells[j].text = title

    # filas de detalle
    for i, row in enumerate(df.itertuples(index=False), start=1):
        cells = tbl.rows[i].cells
        cells[0].text = row.apellido_nombre
        cells[1].text = str(row.cuil)
        cells[2].text = str(row.formulario)
        cells[3].text = str(row.puntaje_total)
        cells[4].text = row.calificacion

    # fila TOTAL
    tot_cells = tbl.rows[n+1].cells
    tot_cells[2].text = "TOTAL"
    tot_cells[3].text = str(n)

    # fila BONIF. CORRESPONDIENTES
    cupo = math.floor(n * 0.3)
    bon_cells = tbl.rows[n+2].cells
    bon_cells[2].text = "BONIF. CORRESPONDIENTES"
    bon_cells[3].text = str(cupo)

    # 4) Cuadro Resumen
    doc.add_paragraph("")
    doc.add_heading("CUADRO RESUMEN", level=2)

    # preparamos datos por nivel 1–6 + TOTAL
    df["nivel_int"] = df["formulario"].astype(int)
    total_por_nivel = df.groupby("nivel_int")["cuil"].count().reindex(range(1,7), fill_value=0)
    dest_por_nivel  = df[df["calificacion"].str.upper()=="DESTACADO"]\
                       .groupby("nivel_int")["cuil"].count()\
                       .reindex(range(1,7), fill_value=0)
    corr_por_nivel  = (total_por_nivel * 0.3).apply(math.floor)
    diff_por_nivel  = dest_por_nivel - corr_por_nivel

    total_col = total_por_nivel.sum()
    dest_col  = dest_por_nivel.sum()
    corr_col  = corr_por_nivel.sum()
    diff_col  = diff_por_nivel.sum()

    niveles = list(range(1,7)) + ["TOTAL"]
    resumen = pd.DataFrame({
        "Cantidad de agentes":     list(total_por_nivel.values) + [total_col],
        "Bonif. otorgadas":        list(dest_por_nivel.values)  + [dest_col],
        "Bonif. correspondientes": list(corr_por_nivel.values) + [corr_col],
        "Diferencia":              list(diff_por_nivel.values) + [diff_col],
    }, index=niveles).T

    tbl2 = doc.add_table(rows=resumen.shape[0] + 1, cols=resumen.shape[1] + 1)
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

    # 5) Nota al pie en cursiva
    dests = df[df["calificacion"].str.upper()=="DESTACADO"]
    max_p = dests["puntaje_total"].max() if not dests.empty else None
    if max_p is not None:
        cand = dests[dests["puntaje_total"]==max_p]["apellido_nombre"].tolist()
        nota = (f"*En este ejemplo el titular de la Unidad de Análisis deberá "
                f"seleccionar un agente bonificado resultará entre {', '.join(cand)} cuyo puntaje es "
                f"{max_p} (DESTACADO).")
        p_n = doc.add_paragraph(nota)
        p_n.italic = True

    # 6) Guardar
    doc.save(path_docx)

def generar_anexo_ii_docx(dataframe, path_docx):
    # (mantenemos tu lógica previa si la necesitas)
    doc = Document()
    doc.add_heading("ANEXO II - LISTADO DE APOYO PARA BONIFICACIÓN POR DESEMPEÑO DESTACADO", level=1)
    table = doc.add_table(rows=1, cols=len(dataframe.columns))
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    for i, col in enumerate(dataframe.columns):
        hdr[i].text = col
    for _, row in dataframe.iterrows():
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    doc.save(path_docx)

def generar_anexo_iii_docx(texto, path_docx):
    doc = Document()
    doc.add_heading("ANEXO III - ACTA DE VEEDURÍA GREMIAL", level=1)
    doc.add_paragraph(texto.strip())
    doc.save(path_docx)

def generar_informe_comite_docx(df, unidad_nombre, total, cupo30, resumen_niveles, path_docx):
    # (sin cambios respecto a tu versión actual)
    doc = Document()
    doc.add_heading("Anexo I – Informe para el Comité", level=1)
    doc.add_paragraph(f"Unidad de Evaluación: {unidad_nombre}")
    doc.add_paragraph("")
    # … resto de tu función …
    doc.save(path_docx)

def generar_cuadro_resumen_docx(df_resumen, path_docx):
    # (sin cambios)
    doc = Document()
    doc.add_heading("Cuadro Resumen de Niveles", level=1)
    # … resto de tu función …
    doc.save(path_docx)


# —————————— Streamlit ——————————

def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>📋 Listado General y Análisis de Tramos</h1>", unsafe_allow_html=True)

    # (todo tu código de carga, filtro, listado general, resumen por formulario, análisis…)

    # 9) ANEXO II – Modelo Listado de Apoyo
    if st.button("📄 Generar Anexo II – Modelo Listado de Apoyo"):
        df_modelo = (
            df_fil
            .sort_values("puntaje_total", ascending=False)
            .loc[:, ["apellido_nombre","cuil","formulario","puntaje_total","calificacion"]]
        )
        unidad_analisis   = seleccion
        unidad_evaluacion = df_fil["unidad_analisis"].iloc[0]

        os.makedirs("tmp_anexos", exist_ok=True)
        path = "tmp_anexos/anexo_ii_modelo.docx"
        generar_anexo_ii_modelo_docx(df_modelo,
                                    unidad_analisis,
                                    unidad_evaluacion,
                                    path)
        with open(path, "rb") as f:
            st.download_button("📥 Descargar Anexo II – Modelo Listado de Apoyo",
                               f, file_name="anexo_ii_modelo.docx")

    # 10) ANEXO III – Acta de Veeduría
    if st.button("📄 Generar Anexo III"):
        tot  = df_fil.shape[0]
        dest = (df_fil["calificacion"].str.upper()=="DESTACADO").sum()
        acta = f"""ACTA DE VEEDURÍA GREMIAL

En la dependencia {seleccion}, con un total de {tot} personas evaluadas, se asignó la bonificación por desempeño destacado a {dest} agentes, de acuerdo al cupo máximo permitido del 30% según la normativa vigente.

La veeduría gremial constató que el procedimiento se realizó conforme a la normativa, y se firmó en señal de conformidad.

Fecha: ...........................................................

Firmas:
- Representante de la unidad de análisis
- Veedor/a gremial"""
        os.makedirs("tmp_anexos", exist_ok=True)
        path4 = "tmp_anexos/anexo_iii.docx"
        generar_anexo_iii_docx(acta, path4)
        with open(path4, "rb") as f:
            st.download_button("📥 Descargar Anexo III", f, file_name="anexo_iii.docx")
