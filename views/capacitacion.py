import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime
from docx import Document
import math

# —————————— Funciones de Word ——————————

def generar_anexo_ii_docx(dataframe, path_docx):
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

def generar_informe_comite_docx(df_detalle, unidad, total, cupo30, path_docx):
    """
    Crea el Anexo I – Informe para el Comité con columnas:
    Apellido | Nombres | CUIL | Nivel | Puntaje Absoluto | Puntaje Relativo | Calificación | Formulario GEDO Nº
    y al final TOTAL y Cupo 30%.
    """
    doc = Document()
    doc.add_heading("Anexo I – Informe para el Comité", level=1)
    doc.add_paragraph(f"Unidad de Evaluación: {unidad}")
    doc.add_paragraph("")

    cols = ["Apellido","Nombres","CUIL","Nivel","Puntaje Absoluto","Puntaje Relativo","Calificación","Formulario GEDO Nº"]
    table = doc.add_table(rows=1 + len(df_detalle) + 2, cols=len(cols))
    table.style = "Table Grid"

    # encabezados
    hdr = table.rows[0].cells
    for i, h in enumerate(cols):
        hdr[i].text = h

    # detalle
    for i, row in enumerate(df_detalle.itertuples(index=False), start=1):
        cells = table.rows[i].cells
        cells[0].text = row.apellido
        cells[1].text = row.nombres
        cells[2].text = str(row.cuil)
        cells[3].text = str(row.nivel)
        cells[4].text = str(row.puntaje_total)
        cells[5].text = f"{row.puntaje_relativo:.3f}"
        cells[6].text = row.calificacion
        cells[7].text = str(row.formulario)

    # totales
    tot_cells = table.rows[-2].cells
    tot_cells[3].text = "TOTAL de agentes"
    tot_cells[4].text = str(total)
    cupo_cells = table.rows[-1].cells
    cupo_cells[3].text = "Cupo Destacados (30%)"
    cupo_cells[4].text = str(cupo30)

    doc.save(path_docx)

def generar_cuadro_resumen_docx(df_resumen, path_docx):
    """
    Crea el Cuadro Resumen de Niveles con filas:
    Cantidad de agentes, Bonif. otorgadas, Bonif. correspondientes, Diferencia
    y columnas niveles 1–6 + TOTAL.
    """
    doc = Document()
    doc.add_heading("Cuadro Resumen de Niveles", level=1)

    niveles = list(df_resumen.columns)
    filas = list(df_resumen.index)

    table = doc.add_table(rows=len(filas) + 1, cols=len(niveles) + 1)
    table.style = "Table Grid"

    # header
    hdr = table.rows[0].cells
    hdr[0].text = "Nivel"
    for j, nivel in enumerate(niveles, start=1):
        hdr[j].text = str(nivel)

    # filas
    for i, fila in enumerate(filas, start=1):
        cells = table.rows[i].cells
        cells[0].text = fila
        for j, nivel in enumerate(niveles, start=1):
            cells[j].text = str(df_resumen.loc[fila, nivel])

    doc.save(path_docx)


# —————————— Streamlit ——————————

def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>📋 Listado General y Análisis de Tramos</h1>", unsafe_allow_html=True)

    # 1) Cargo datos
    evals   = supabase.table("evaluaciones").select("*").execute().data or []
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data or []
    unids   = supabase.table("unidades_evaluacion").select("*").execute().data or []

    if not evals or not unids:
        st.warning("No hay datos en 'evaluaciones' o 'unidades_evaluacion'.")
        return

    # 2) Filtrar anuladas/inactivas y mapear nombres
    evals = [e for e in evals if not e.get("anulada", False) and e.get("activo", False)]
    mapa  = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    # 3) Listado general y descarga Excel
    filas = []
    for e in evals:
        c = str(e.get("cuil",""))
        filas.append({
            "CUIL": c,
            "AGENTE": mapa.get(e.get("cuil"), "Desconocido"),
            "FORMULARIO": e.get("formulario",""),
            "CALIFICACIÓN": e.get("calificacion",""),
            "PUNTAJE TOTAL": e.get("puntaje_total") or 0,
            "DEPENDENCIA GENERAL": e.get("dependencia_general","")
        })
    df_gen = pd.DataFrame(filas)
    st.markdown("#### 📑 Listado General de Evaluaciones")
    st.dataframe(df_gen, use_container_width=True)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df_gen.to_excel(w, index=False, sheet_name="Evaluaciones")
    st.download_button(
        "📥 Descargar Listado General (Excel)",
        buf.getvalue(),
        file_name="listado_general.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # 4) Selección de Dirección General / Residual
    df_ev = pd.DataFrame(evals)
    df_un = pd.DataFrame(unids)
    resid_ids = df_un[df_un["residual"] == True]["unidad_analisis"].unique()
    df_ev["residual_general"] = df_ev["unidad_analisis"].isin(resid_ids)

    opts = sorted(df_ev["dependencia_general"].dropna().unique())
    opts.append("RESIDUAL GENERAL")
    seleccion = st.selectbox("Seleccioná una Dirección General", opts)

    if seleccion == "RESIDUAL GENERAL":
        df_fil = df_ev[df_ev["residual_general"]]
    else:
        df_fil = df_ev[df_ev["dependencia_general"] == seleccion]

    if df_fil.empty:
        st.info("No hay evaluaciones para esa dependencia.")
        return

    # 5) Resumen por Formulario
    res_for = (
        df_fil
        .groupby("formulario")
        .agg(
            evaluados_total=("cuil","count"),
            destacados_total=("calificacion", lambda x: (pd.Series(x)=="Destacado").sum())
        )
        .reset_index()
    )
    res_for["% Destacados"] = (res_for["destacados_total"] / res_for["evaluados_total"] * 100).round(2)
    res_for["Cupo 30%"]     = (res_for["evaluados_total"] * 0.3).round().astype(int)
    res_for["Cupo 10%"]     = (res_for["evaluados_total"] * 0.1).round().astype(int)
    st.markdown(f"#### 🗂 Resumen por Formulario — {seleccion}")
    st.dataframe(res_for, use_container_width=True)

    # 6) Análisis detallado por Unidad de Análisis
    regs = []
    for ua, grp in df_fil.groupby("unidad_analisis"):
        tot      = len(grp)
        dest     = grp[grp["calificacion"]=="Destacado"]
        n_dest   = len(dest)
        pct      = round(n_dest / tot * 100, 2) if tot else 0
        c30      = round(tot * 0.3)
        c10      = round(tot * 0.1)
        dest_ord = dest.sort_values("puntaje_relativo", ascending=False)
        orden    = dest_ord["cuil"].astype(str).tolist()
        bonif    = orden[:c10]

        regs.append({
            "unidad_analisis": ua,
            "Evaluados": tot,
            "Destacados": n_dest,
            "% Destacados": pct,
            "Cupo 30%": c30,
            "Cupo 10%": c10,
            "Bonificados": len(bonif),
            "Fecha Análisis": datetime.now().isoformat(),
            "List CUIL Bonif.": "; ".join(bonif),
            "Orden Puntaje": "; ".join(orden)
        })
    df_det = pd.DataFrame(regs)
    st.markdown(f"#### 🔍 Análisis por Unidad de Análisis — {seleccion}")
    st.dataframe(df_det, use_container_width=True)

    # 7) Anexo I – Informe para el Comité
    if st.button("📄 Generar Anexo I – Informe para el Comité"):
        unidad_eval = df_fil["unidad_analisis"].iloc[0]
        # Preparo detalle con columnas necesarias
        df_inf = df_fil.copy()
        df_inf["apellido"]          = df_inf["apellido_nombre"]
        df_inf["nombres"]           = ""  # si no tienes campo de nombres separado
        df_inf["nivel"]             = df_inf["nivel"] if "nivel" in df_inf.columns else df_inf["formulario"]
        df_inf["puntaje_total"]     = df_inf["puntaje_total"]
        df_inf["puntaje_relativo"]  = df_inf["puntaje_relativo"]
        df_inf["calificacion"]      = df_inf["calificacion"]
        df_inf["formulario"]        = df_inf["formulario"]
        df_inf = df_inf[["apellido","nombres","cuil","nivel","puntaje_total","puntaje_relativo","calificacion","formulario"]]

        total  = df_inf.shape[0]
        cupo30 = int(round(total * 0.3))

        os.makedirs("tmp_anexos", exist_ok=True)
        path1 = "tmp_anexos/anexo_I_informe_comite.docx"
        generar_informe_comite_docx(df_inf, unidad_eval, total, cupo30, path1)
        with open(path1, "rb") as f:
            st.download_button("📥 Descargar Anexo I – Informe para el Comité",
                               f, file_name="anexo_I_informe_comite.docx")

    # 8) Cuadro Resumen de Niveles
    if st.button("📄 Generar Cuadro Resumen de Niveles"):
        # agrupo por nivel
        df_inf = df_fil.copy()
        if "nivel" not in df_inf.columns:
            df_inf["nivel"] = df_inf["formulario"]
        resumen_niveles = (
            df_inf
            .groupby("nivel")
            .agg(
                Cantidad_de_agentes=("cuil","count"),
                Bonif_otorgadas=("calificacion", lambda x: (pd.Series(x)=="Destacado").sum())
            )
            .reindex([1,2,3,4,5,6], fill_value=0)
        )
        resumen_niveles["Bonif_correspondientes"] = (resumen_niveles["Cantidad_de_agentes"] * 0.3).round().astype(int)
        resumen_niveles["Diferencia"]             = resumen_niveles["Bonif_otorgadas"] - resumen_niveles["Bonif_correspondientes"]
        resumen_niveles["TOTAL"]                  = resumen_niveles.sum(axis=1)

        df_res = pd.DataFrame({
            "Cantidad de agentes":      resumen_niveles["Cantidad_de_agentes"],
            "Bonif. otorgadas":         resumen_niveles["Bonif_otorgadas"],
            "Bonif. correspondientes":  resumen_niveles["Bonif_correspondientes"],
            "Diferencia":               resumen_niveles["Diferencia"]
        }).T

        os.makedirs("tmp_anexos", exist_ok=True)
        path2 = "tmp_anexos/cuadro_resumen_niveles.docx"
        generar_cuadro_resumen_docx(df_res, path2)
        with open(path2, "rb") as f:
            st.download_button("📥 Descargar Cuadro Resumen de Niveles",
                               f, file_name="cuadro_resumen_niveles.docx")

    # 9) ANEXO II - Listado de Apoyo (mantiene lógica previa)
    if st.button("📄 Generar ANEXO II"):
        ua0  = df_fil["unidad_analisis"].iloc[0]
        reg0 = next(r for r in regs if r["unidad_analisis"] == ua0)
        c10  = reg0["Cupo 10%"]

        df_a = (
            df_fil
            .assign(cuil=lambda d: d["cuil"].astype(str))
            .sort_values("puntaje_relativo", ascending=False)
            .reset_index(drop=True)
        )
        df_a["ORDEN"]        = df_a.index + 1
        df_a["BONIFICACIÓN"] = df_a["ORDEN"].apply(lambda x: "Sí" if x <= c10 else "")

        df_anexo = (
            df_a
            .rename(columns={
                "apellido_nombre":"APELLIDO Y NOMBRE",
                "formulario":"NIVEL",
                "calificacion":"CALIFICACIÓN"
            })
            [["APELLIDO Y NOMBRE","cuil","NIVEL","CALIFICACIÓN","ORDEN","BONIFICACIÓN"]]
        )

        os.makedirs("tmp_anexos", exist_ok=True)
        path3 = "tmp_anexos/anexo_ii.docx"
        generar_anexo_ii_docx(df_anexo, path3)
        with open(path3, "rb") as f:
            st.download_button("📥 Descargar ANEXO II", f, file_name="anexo_ii.docx")

    # 10) ANEXO III - Acta de Veeduría
    if st.button("📄 Generar ANEXO III"):
        tot  = df_fil.shape[0]
        dest = (df_fil["calificacion"]=="Destacado").sum()
        acta = f"""ACTA DE VEEDURÍA GREMIAL

En la dependencia {seleccion}, con un total de {tot} personas evaluadas, se asignó la bonificación por desempeño destacado a {dest} agentes, de acuerdo al cupo máximo permitido del 30% según la normativa vigente.

La veeduría gremial constató que el procedimiento se realizó conforme a la normativa, y se firmó en señal de conformidad.

Fecha: ........................................................

Firmas:
- Representante de la unidad de análisis
- Veedor/a gremial"""
        os.makedirs("tmp_anexos", exist_ok=True)
        path4 = "tmp_anexos/anexo_iii.docx"
        generar_anexo_iii_docx(acta, path4)
        with open(path4, "rb") as f:
            st.download_button("📥 Descargar ANEXO III", f, file_name="anexo_iii.docx")
