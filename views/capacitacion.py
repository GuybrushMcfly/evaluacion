import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime
from docx import Document
import math

def generar_anexo_ii_docx(dataframe, path_docx):
    doc = Document()
    doc.add_heading("ANEXO II - LISTADO DE APOYO PARA BONIFICACIÓN POR DESEMPEÑO DESTACADO", level=1)
    table = doc.add_table(rows=1, cols=len(dataframe.columns))
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    for i, col in enumerate(dataframe.columns):
        hdr[i].text = col
    for _, row in dataframe.iterrows():
        row_cells = table.add_row().cells
        for i, val in enumerate(row):
            row_cells[i].text = str(val)
    doc.save(path_docx)

def generar_anexo_iii_docx(texto, path_docx):
    doc = Document()
    doc.add_heading("ANEXO III - ACTA DE VEEDURÍA GREMIAL", level=1)
    doc.add_paragraph(texto.strip())
    doc.save(path_docx)

def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>📋 Listado General y Análisis de Tramos</h1>", unsafe_allow_html=True)

    # 1) Cargo datos
    evals   = supabase.table("evaluaciones").select("*").execute().data or []
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data or []
    unids   = supabase.table("unidades_evaluacion").select("*").execute().data or []

    if not evals or not unids:
        st.warning("No hay datos en 'evaluaciones' o 'unidades_evaluacion'.")
        return

    # filtro y mapeo
    evals = [e for e in evals if not e.get("anulada", False) and e.get("activo", False)]
    mapa = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    # 2) Listado general + descarga Excel
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

    # 3) Selección de Dirección General o Residual
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

    # 4) Resumen por formulario
    res_for = (
        df_fil
        .groupby("formulario")
        .agg(
            evaluados_total=("cuil","count"),
            destacados_total=("calificacion", lambda x: (pd.Series(x)=="Destacado").sum())
        )
        .reset_index()
    )
    res_for["porcentaje_destacados"] = (
        (res_for["destacados_total"] / res_for["evaluados_total"] * 100).round(2)
    )
    res_for["cupo_max_30"] = (res_for["evaluados_total"] * 0.3).round().astype(int)
    st.markdown(f"#### 🗂 Resumen por Formulario - {seleccion}")
    st.dataframe(res_for, use_container_width=True)

    # 5) Análisis detallado por unidad_analisis dentro de la dependencia seleccionada
    regs = []
    for ua, grp in df_fil.groupby("unidad_analisis"):
        tot = len(grp)
        dest = grp[grp["calificacion"]=="Destacado"]
        n_dest = len(dest)
        pct = round(n_dest / tot * 100, 2) if tot else 0
        c30 = round(tot * 0.3)
        c10 = round(tot * 0.1)
        dest_ord = dest.sort_values("puntaje_relativo", ascending=False)
        orden = dest_ord["cuil"].astype(str).tolist()
        bonif = orden[:c10]
        regs.append({
            "unidad_analisis": ua,
            "evaluados_total": tot,
            "destacados_total": n_dest,
            "porcentaje_destacados": pct,
            "cupo_max_30": c30,
            "cupo_max_10": c10,
            "bonificados_cnt": len(bonif),
            "fecha_analisis": datetime.now().isoformat()
        })
    df_det = pd.DataFrame(regs)
    st.markdown(f"#### 🔍 Análisis por Unidad de Análisis - {seleccion}")
    st.dataframe(df_det, use_container_width=True)

    # 6) Generar ANEXO II
    if st.button("📄 Generar ANEXO II - Listado de Apoyo"):
        ua0 = df_fil["unidad_analisis"].iloc[0]
        reg0 = next(r for r in regs if r["unidad_analisis"] == ua0)
        orden = [
            str(x) for x in
            df_fil[df_fil["calificacion"]=="Destacado"]
                .sort_values("puntaje_relativo", ascending=False)["cuil"].tolist()
        ]
        bonif = orden[: reg0["cupo_max_10"] ]

        df_a = df_fil.copy()
        df_a["cuil"] = df_a["cuil"].astype(str)
        df_a = df_a[df_a["cuil"].isin(orden)]
        df_a["ORDEN"] = df_a["cuil"].apply(lambda x: orden.index(x)+1)
        df_a["BONIFICACIÓN"] = df_a["cuil"].apply(lambda x: x in bonif)

        anexo = (
            df_a
            .rename(columns={
                "apellido_nombre":"APELLIDO Y NOMBRE",
                "formulario":"NIVEL",
                "calificacion":"CALIFICACIÓN"
            })
            [["APELLIDO Y NOMBRE","cuil","NIVEL","CALIFICACIÓN","ORDEN","BONIFICACIÓN"]]
            .sort_values("ORDEN")
        )

        os.makedirs("tmp_anexos", exist_ok=True)
        generar_anexo_ii_docx(anexo, "tmp_anexos/anexo_ii.docx")
        with open("tmp_anexos/anexo_ii.docx","rb") as f:
            st.download_button("📥 Descargar ANEXO II", f, file_name="anexo_ii.docx")

    # 7) Generar ANEXO III
    if st.button("📄 Generar ANEXO III - Acta de Veeduría"):
        tot = df_fil.shape[0]
        dest = (df_fil["calificacion"]=="Destacado").sum()
        acta = f"""ACTA DE VEEDURÍA GREMIAL

En la dependencia {seleccion}, con un total de {tot} personas evaluadas, se asignó la bonificación por desempeño destacado a {dest} agentes, de acuerdo al cupo máximo permitido del 30% según la normativa vigente.

La veeduría gremial constató que el procedimiento se realizó conforme a la normativa, y se firmó en señal de conformidad.

Fecha: ........................................................

Firmas:
- Representante de la unidad de análisis
- Veedor/a gremial"""
        os.makedirs("tmp_anexos", exist_ok=True)
        generar_anexo_iii_docx(acta, "tmp_anexos/anexo_iii.docx")
        with open("tmp_anexos/anexo_iii.docx","rb") as f:
            st.download_button("📥 Descargar ANEXO III", f, file_name="anexo_iii.docx")
