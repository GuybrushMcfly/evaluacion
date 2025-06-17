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
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    doc.save(path_docx)

def generar_anexo_iii_docx(texto, path_docx):
    doc = Document()
    doc.add_heading("ANEXO III - ACTA DE VEEDURÍA GREMIAL", level=1)
    doc.add_paragraph(texto.strip())
    doc.save(path_docx)

def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>📋 Listado General y Análisis de Tramos</h1>", unsafe_allow_html=True)

    # 1) Cargando datos
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
    res_for["% Destacados"]    = (res_for["destacados_total"] / res_for["evaluados_total"] * 100).round(2)
    res_for["Cupo 30%"]        = (res_for["evaluados_total"] * 0.3).round().astype(int)
    res_for["Cupo 10%"]        = (res_for["evaluados_total"] * 0.1).round().astype(int)
    st.markdown(f"#### 🗂 Resumen por Formulario — {seleccion}")
    st.dataframe(res_for, use_container_width=True)

    # 6) Análisis detallado por Unidad de Análisis
    regs = []
    for ua, grp in df_fil.groupby("unidad_analisis"):
        tot   = len(grp)
        dest  = grp[grp["calificacion"]=="Destacado"]
        n_dest = len(dest)
        pct   = round(n_dest / tot * 100, 2) if tot else 0
        c30   = round(tot * 0.3)
        c10   = round(tot * 0.1)
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

    # 7) ANEXO II - Listado de Apoyo
    if st.button("📄 Generar ANEXO II"):
        # Tomo la primera unidad del filtro (puede adaptarse si quieres un select adicional)
        ua0   = df_fil["unidad_analisis"].iloc[0]
        reg0  = next(r for r in regs if r["unidad_analisis"] == ua0)
        c10   = reg0["Cupo 10%"]

        # Ordenar todos y marcar bonificación solo para los cupos 10%
        df_a  = (
            df_fil
            .assign(cuil=lambda d: d["cuil"].astype(str))
            .sort_values("puntaje_relativo", ascending=False)
            .reset_index(drop=True)
        )
        df_a["ORDEN"] = df_a.index + 1
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
        generar_anexo_ii_docx(df_anexo, "tmp_anexos/anexo_ii.docx")
        with open("tmp_anexos/anexo_ii.docx","rb") as f:
            st.download_button("📥 Descargar ANEXO II", f, file_name="anexo_ii.docx")

    # 8) ANEXO III - Acta de Veeduría
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
        generar_anexo_iii_docx(acta, "tmp_anexos/anexo_iii.docx")
        with open("tmp_anexos/anexo_iii.docx","rb") as f:
            st.download_button("📥 Descargar ANEXO III", f, file_name="anexo_iii.docx")
