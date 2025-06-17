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

def limpiar_registro(r):
    # Convierte datetime a string ISO
    if isinstance(r.get("fecha_analisis"), datetime):
        r["fecha_analisis"] = r["fecha_analisis"].isoformat()
    # Asegura enteros en campos numéricos
    for key in ["anio_evaluacion", "evaluados_total", "cupo_maximo_30", "destacados_total"]:
        val = r.get(key)
        if val is None or (isinstance(val, float) and math.isnan(val)):
            r[key] = 0
        else:
            r[key] = int(val)
    # Limpia listas
    for key in ["bonificados_cuils", "orden_puntaje"]:
        lista = r.get(key) or []
        r[key] = [str(x) for x in lista if x is not None]
    return r

def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>Análisis de Capacitación</h1>", unsafe_allow_html=True)

    # 1) Carga de datos
    evaluaciones = supabase.table("evaluaciones").select("*").execute().data or []
    agentes       = supabase.table("agentes").select("cuil, apellido_nombre").execute().data or []
    unidades      = supabase.table("unidades_evaluacion").select("*").execute().data or []

    if not evaluaciones or not unidades:
        st.warning("No hay datos en 'evaluaciones' o 'unidades_evaluacion'.")
        return

    # 2) Filtrado inicial y mapeo de agentes
    evaluaciones = [e for e in evaluaciones if not e.get("anulada", False)]
    mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    # ---- SECCIÓN 1: RESUMEN INDIVIDUAL Y EXCEL ----
    filas_tabla = []
    filas_excel = []
    for e in evaluaciones:
        cuil         = str(e.get("cuil",""))
        agente       = mapa_agentes.get(e.get("cuil"), "Desconocido")
        resumen_fp   = ", ".join(f"{k} ({v})" for k,v in (e.get("factor_puntaje") or {}).items())

        filas_tabla.append({
            "AGENTE": agente,
            "FORMULARIO": e.get("formulario",""),
            "CALIFICACIÓN": e.get("calificacion",""),
            "TOTAL": e.get("puntaje_total","")
        })
        filas_excel.append({
            "CUIL": cuil,
            "AGENTE": agente,
            "FORMULARIO": e.get("formulario",""),
            "FACTOR/PUNTAJE": resumen_fp,
            "CALIFICACIÓN": e.get("calificacion",""),
            "PUNTAJE TOTAL": e.get("puntaje_total") or 0,
            "PUNTAJE MÁXIMO": e.get("puntaje_maximo") or 0,
            "PUNTAJE RELATIVO": float(e.get("puntaje_relativo") or 0.0),
            "DEPENDENCIA": e.get("dependencia",""),
            "DEPENDENCIA GENERAL": e.get("dependencia_general","")
        })

    st.markdown("### 📋 Resumen Individual")
    st.dataframe(pd.DataFrame(filas_tabla), use_container_width=True)

    df_excel = pd.DataFrame(filas_excel)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_excel.to_excel(writer, index=False, sheet_name="Resumen")
    st.download_button(
        label="📥 Descargar Excel",
        data=buffer.getvalue(),
        file_name="resumen_capacitacion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # 3) CÁLCULO DINÁMICO DE ANÁLISIS POR UNIDAD
    df_eval = pd.DataFrame(evaluaciones)
    df_un   = pd.DataFrame(unidades)
    df_eval = df_eval[df_eval["activo"] == True]
    resid_ids = df_un[df_un["residual"] == True]["unidad_analisis"].unique()
    df_eval["residual_general"] = df_eval["unidad_analisis"].isin(resid_ids)

    registros = []
    for ua, grp in df_eval.groupby("unidad_analisis"):
        total_evals   = len(grp)
        cupo_30       = round(total_evals * 0.3)
        cupo_10       = round(total_evals * 0.10)
        dest          = grp[grp["calificacion"]=="Destacado"]
        dest_ord      = dest.sort_values("puntaje_relativo",ascending=False)
        bonificados   = dest_ord["cuil"].astype(str).tolist()[:cupo_10]
        orden_puntaje = dest_ord["cuil"].astype(str).tolist()
        anioms        = grp["anio_evaluacion"].dropna().astype(int)
        anio_eval     = int(anioms.max()) if not anioms.empty else 0

        reg = {
            "unidad_analisis": ua,
            "anio_evaluacion": anio_eval,
            "evaluados_total": total_evals,
            "destacados_total": len(dest),
            "cupo_maximo_30": cupo_30,
            "bonificados_cuils": bonificados,
            "orden_puntaje": orden_puntaje,
            "fecha_analisis": datetime.now()
        }
        registros.append(limpiar_registro(reg))

    df_ana = pd.DataFrame(registros)
    st.markdown("### 📊 Análisis Dinámico por Unidad")
    st.dataframe(df_ana, use_container_width=True)

    # 4) SECCIÓN DE ANEXOS
    opts = sorted(df_eval["dependencia_general"].dropna().unique().tolist())
    opts.append("RESIDUAL GENERAL")
    seleccion = st.selectbox("Seleccioná una Dirección General", opts)

    if seleccion == "RESIDUAL GENERAL":
        df_fil = df_eval[df_eval["residual_general"]]
    else:
        df_fil = df_eval[df_eval["dependencia_general"]==seleccion]

    if df_fil.empty:
        st.info("No hay evaluaciones para esta dependencia.")
        return

    resumen = df_fil.groupby("formulario").agg(
        evaluados_total=("cuil","count"),
        destacados_total=("calificacion", lambda x: (pd.Series(x)=="Destacado").sum())
    ).reset_index()
    resumen["cupo_maximo_30"] = (resumen["evaluados_total"]*0.3).round().astype(int)
    st.markdown("### 🗂 Resumen por Formulario")
    st.dataframe(resumen, use_container_width=True)

    # ANEXO II
    if st.button("Generar ANEXO II - Listado de Apoyo"):
        ua = df_fil["unidad_analisis"].iloc[0]
        reg = df_ana[df_ana["unidad_analisis"]==ua].iloc[0]

        bon = reg["bonificados_cuils"]
        ordp = reg["orden_puntaje"]

        df_form = df_fil.copy()
        df_form["cuil"] = df_form["cuil"].astype(str)
        df_form = df_form[df_form["cuil"].isin(ordp)]
        df_form["ORDEN"] = df_form["cuil"].apply(lambda x: ordp.index(x)+1)
        df_form["BONIFICACIÓN"] = df_form["cuil"].apply(lambda x: x in bon)

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
            st.download_button("📥 Descargar ANEXO II en Word", f, file_name="anexo_ii.docx")

    # ANEXO III
    if st.button("Generar ANEXO III - Acta de Veeduría"):
        total_eval = df_fil.shape[0]
        total_dest = (df_fil["calificacion"]=="Destacado").sum()
        acta = f"""ACTA DE VEEDURÍA GREMIAL

En la dependencia {seleccion}, con un total de {total_eval} personas evaluadas, se asignó la bonificación por desempeño destacado a {total_dest} agentes, de acuerdo al cupo máximo permitido del 30% según la normativa vigente.

La veeduría gremial constató que el procedimiento se realizó conforme a la normativa, y se firmó en señal de conformidad.

Fecha: ........................................................

Firmas:
- Representante de la unidad de análisis
- Veedor/a gremial"""
        generar_anexo_iii_docx(acta, "tmp_anexos/anexo_iii.docx")
        with open("tmp_anexos/anexo_iii.docx","rb") as f:
            st.download_button("📥 Descargar ANEXO III en Word", f, file_name="anexo_iii.docx")
