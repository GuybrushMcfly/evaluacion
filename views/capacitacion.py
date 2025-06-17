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
    hdr_cells = table.rows[0].cells
    for i, column in enumerate(dataframe.columns):
        hdr_cells[i].text = column
    for _, row in dataframe.iterrows():
        row_cells = table.add_row().cells
        for i, item in enumerate(row):
            row_cells[i].text = str(item)
    doc.save(path_docx)

def generar_anexo_iii_docx(texto, path_docx):
    doc = Document()
    doc.add_heading("ANEXO III - ACTA DE VEEDURÍA GREMIAL", level=1)
    doc.add_paragraph(texto.strip())
    doc.save(path_docx)

def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>📊 Análisis de Tramos y Anexos</h1>", unsafe_allow_html=True)

    # 1) Carga de datos
    evaluaciones = supabase.table("evaluaciones").select("*").execute().data or []
    agentes       = supabase.table("agentes").select("cuil, apellido_nombre").execute().data or []
    unidades      = supabase.table("unidades_evaluacion").select("*").execute().data or []

    if not evaluaciones or not unidades:
        st.warning("No hay datos disponibles en evaluaciones o unidades_evaluacion.")
        return

    # 2) Filtrado y mapeo
    evaluaciones = [e for e in evaluaciones if not e.get("anulada", False)]
    mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    # 3) Análisis dinámico por unidad_analisis
    df_eval = pd.DataFrame(evaluaciones)
    df_un   = pd.DataFrame(unidades)

    # Solo activos
    df_eval = df_eval[df_eval["activo"] == True]

    # Marcamos residual_general
    resid_ids = df_un[df_un["residual"] == True]["unidad_analisis"].unique()
    df_eval["residual_general"] = df_eval["unidad_analisis"].isin(resid_ids)

    registros = []
    for ua, grp in df_eval.groupby("unidad_analisis"):
        total = len(grp)
        dest  = grp[grp["calificacion"] == "Destacado"]
        n_dest = len(dest)
        pct_dest = round((n_dest / total * 100), 2) if total else 0
        cupo30 = round(total * 0.3)
        cupo10 = round(total * 0.1)

        # Orden y bonificados
        dest_ord = dest.sort_values("puntaje_relativo", ascending=False)
        orden = dest_ord["cuil"].astype(str).tolist()
        bonif = orden[:cupo10]

        registros.append({
            "unidad_analisis": ua,
            "evaluados_total": total,
            "destacados_total": n_dest,
            "porcentaje_destacados": pct_dest,
            "cupo_maximo_30": cupo30,
            "cupo_maximo_10": cupo10,
            "bonificados_cuils": bonif,
            "orden_puntaje": orden,
            "fecha_analisis": datetime.now().isoformat()
        })

    df_ana = pd.DataFrame(registros)

    # 4) Mostrar análisis en pantalla
    st.markdown("#### 📈 Métricas por Unidad de Análisis")
    st.dataframe(
        df_ana[[
            "unidad_analisis",
            "evaluados_total",
            "destacados_total",
            "porcentaje_destacados",
            "cupo_maximo_30"
        ]],
        use_container_width=True
    )

    # 5) Selección de Dirección General o Residual
    opts = sorted(df_eval["dependencia_general"].dropna().unique().tolist())
    opts.append("RESIDUAL GENERAL")
    seleccion = st.selectbox("Seleccioná una Dirección General", opts)

    if seleccion == "RESIDUAL GENERAL":
        df_fil = df_eval[df_eval["residual_general"]]
    else:
        df_fil = df_eval[df_eval["dependencia_general"] == seleccion]

    if df_fil.empty:
        st.info("No hay evaluaciones para esta dependencia.")
        return

    # 6) Resumen por formulario (opcional)
    resumen = (
        df_fil
        .groupby("formulario")
        .agg(
            evaluados_total=("cuil","count"),
            destacados_total=("calificacion", lambda x: (pd.Series(x)=="Destacado").sum())
        )
        .reset_index()
    )
    resumen["cupo_maximo_30"] = (resumen["evaluados_total"] * 0.3).round().astype(int)
    st.markdown("#### 🗂 Resumen por Formulario para esta Dirección")
    st.dataframe(resumen, use_container_width=True)


    # 7) Generar ANEXO II
    if st.button("📄 Generar ANEXO II - Listado de Apoyo"):
        ua = df_fil["unidad_analisis"].iloc[0]
        reg = df_ana[df_ana["unidad_analisis"] == ua].iloc[0]
        orden = reg["orden_puntaje"]
        bonif = reg["bonificados_cuils"]

        df_form = df_fil.copy()
        df_form["cuil"] = df_form["cuil"].astype(str)
        df_form = df_form[df_form["cuil"].isin(orden)]
        df_form["ORDEN"] = df_form["cuil"].apply(lambda x: orden.index(x) + 1)
        df_form["BONIFICACIÓN"] = df_form["cuil"].apply(lambda x: x in bonif)

        df_anexo = (
            df_form
            .rename(columns={
                "apellido_nombre":"APELLIDO Y NOMBRE",
                "formulario":"NIVEL",
                "calificacion":"CALIFICACIÓN"
            })
            [["APELLIDO Y NOMBRE","cuil","NIVEL","CALIFICACIÓN","ORDEN","BONIFICACIÓN"]]
            .sort_values("ORDEN")
        )

        os.makedirs("tmp_anexos", exist_ok=True)
        generar_anexo_ii_docx(df_anexo, "tmp_anexos/anexo_ii.docx")
        with open("tmp_anexos/anexo_ii.docx","rb") as f:
            st.download_button("📥 Descargar ANEXO II", f, file_name="anexo_ii.docx")

    # 8) Generar ANEXO III
    if st.button("📄 Generar ANEXO III - Acta de Veeduría"):
        total_eval = df_fil.shape[0]
        total_dest = (df_fil["calificacion"] == "Destacado").sum()
        acta = f"""ACTA DE VEEDURÍA GREMIAL

En la dependencia {seleccion}, con un total de {total_eval} personas evaluadas, se asignó la bonificación por desempeño destacado a {total_dest} agentes, de acuerdo al cupo máximo permitido del 30% según la normativa vigente.

La veeduría gremial constató que el procedimiento se realizó conforme a la normativa, y se firmó en señal de conformidad.

Fecha: ........................................................

Firmas:
- Representante de la unidad de análisis
- Veedor/a gremial"""
        os.makedirs("tmp_anexos", exist_ok=True)
        generar_anexo_iii_docx(acta, "tmp_anexos/anexo_iii.docx")
        with open("tmp_anexos/anexo_iii.docx","rb") as f:
            st.download_button("📥 Descargar ANEXO III", f, file_name="anexo_iii.docx")
