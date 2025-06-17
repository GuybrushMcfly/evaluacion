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
    # Limpia campos numéricos de NaN o None y convierte a int (menos destacados_total, que va como str)
    for key in ["anio_evaluacion", "evaluados_total", "cupo_maximo_30"]:
        val = r.get(key)
        if val is None or (isinstance(val, float) and math.isnan(val)):
            r[key] = 0
        else:
            r[key] = int(val)
    # destacados_total va como str por el esquema
    if "destacados_total" in r:
        val = r["destacados_total"]
        try:
            r["destacados_total"] = str(int(val))
        except Exception:
            r["destacados_total"] = str(val) if val is not None else "0"
    # Limpia listas JSONB, elimina None y convierte todo a string
    for key in ["bonificados_cuils", "orden_puntaje"]:
        lista = r.get(key)
        if lista is None:
            r[key] = []
        else:
            r[key] = [str(x) for x in lista if x is not None]
    return r

def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>Análisis de Capacitación</h1>", unsafe_allow_html=True)

    # Carga de datos
    evaluaciones = supabase.table("evaluaciones").select("*").execute().data
    agentes       = supabase.table("agentes").select("cuil, apellido_nombre").execute().data
    unidades      = supabase.table("unidades_evaluacion").select("*").execute().data
    analisis_prev = supabase.table("analisis_evaluaciones").select("*").execute().data

    if not evaluaciones or not unidades:
        st.warning("No hay datos disponibles.")
        return

    # Filtrado inicial y mapeo de agentes
    evaluaciones = [e for e in evaluaciones if not e.get("anulada", False)]
    mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    # ---- SECCION 1: EXCEL ----
    filas_tabla = []
    filas_excel = []
    for e in evaluaciones:
        cuil         = e.get("cuil", "")
        agente       = mapa_agentes.get(cuil, "Desconocido")
        formulario   = e.get("formulario", "")
        calificacion = e.get("calificacion", "")
        total        = e.get("puntaje_total", "")
        factores     = e.get("factor_puntaje") or {}
        resumen_fp   = ", ".join([f"{k} ({v})" for k,v in factores.items()])

        filas_tabla.append({
            "AGENTE": agente,
            "FORMULARIO": formulario,
            "CALIFICACION": calificacion,
            "TOTAL": total
        })

        filas_excel.append({
            "CUIL": cuil,
            "AGENTE": agente,
            "FORMULARIO": formulario,
            "FACTOR/PUNTAJE": resumen_fp,
            "CALIFICACION": calificacion,
            "PUNTAJE TOTAL": total,
            "PUNTAJE MÁXIMO": e.get("puntaje_maximo") or 0,
            "PUNTAJE RELATIVO": float(e.get("puntaje_relativo") or 0.0),
            "DEPENDENCIA": e.get("dependencia", ""),
            "DEPENDENCIA GENERAL": e.get("dependencia_general", "")
        })

    st.markdown("### Resumen Individual")
    st.dataframe(pd.DataFrame(filas_tabla), use_container_width=True)

    df_excel = pd.DataFrame(filas_excel)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_excel.to_excel(writer, index=False, sheet_name="Resumen")
    st.download_button(
        label="Descargar Excel",
        data=buffer.getvalue(),
        file_name="resumen_capacitacion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ---- SECCION 2: ANALISIS ----
    if st.button("Ejecutar Análisis de Evaluaciones"):
        df = pd.DataFrame(evaluaciones)
        df_un = pd.DataFrame(unidades)
        df = df[df["activo"] == True]
        df["residual_general"] = df["unidad_analisis"].isin(
            df_un[df_un["residual"] == True]["unidad_analisis"].unique()
        )

        registros = []
        for ua, grp in df.groupby("unidad_analisis"):
            total_evals      = len(grp)
            cupo_30          = round(total_evals * 0.3)
            cupo_10          = round(total_evals * 0.10)
            dest             = grp[grp["calificacion"] == "Destacado"]
            dest_ord         = dest.sort_values("puntaje_relativo", ascending=False)
            bonificados      = dest_ord["cuil"].tolist()[:cupo_10]
            orden_puntaje    = dest_ord["cuil"].tolist()
            anio_vals        = grp["anio_evaluacion"].dropna().astype(int)
            anio_eval        = int(anio_vals.max()) if not anio_vals.empty else 0

            reg = {
                "unidad_analisis": ua,
                "anio_evaluacion": anio_eval,
                "evaluados_total": total_evals,
                "destacados_total": len(dest),
                "cupo_maximo_30": cupo_30,
                "bonificados_cuils": bonificados,
                "orden_puntaje": orden_puntaje,
                "fecha_analisis": datetime.now().isoformat()
            }
            reg = limpiar_registro(reg)
            registros.append(reg)

        # Reemplazar análisis previo
        supabase.table("analisis_evaluaciones").delete().neq("unidad_analisis", "").execute()
        for r in registros:
            try:
                supabase.table("analisis_evaluaciones").insert(r).execute()
            except Exception as e:
                st.error(f"Error en insert: {e}")
                st.write(r)
        st.success("Análisis guardado en la tabla analisis_evaluaciones.")

    # ---- SECCION 3: ANEXOS ----
    df_eval   = pd.DataFrame(evaluaciones)
    df_resid  = pd.DataFrame(unidades)
    df_ana    = pd.DataFrame(analisis_prev)
    df_eval   = df_eval[df_eval["activo"] == True]
    resid_ids = df_resid[df_resid["residual"] == True]["unidad_analisis"].unique()
    df_eval["residual_general"] = df_eval["unidad_analisis"].isin(resid_ids)

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

    resumen = df_fil.groupby("formulario").agg(
        evaluados_total=("cuil","count"),
        destacados_total=("calificacion", lambda x: (pd.Series(x)=="Destacado").sum())
    ).reset_index()
    resumen["cupo_maximo_30"] = (resumen["evaluados_total"]*0.3).round().astype(int)
    st.dataframe(resumen)

    if st.button("Generar ANEXO II - Listado de Apoyo"):
        anexos = []
        ua = df_fil["unidad_analisis"].iloc[0]
        ana = df_ana[df_ana["unidad_analisis"] == ua]
        if not ana.empty:
            bon = ana.iloc[0]["bonificados_cuils"]
            ordp = ana.iloc[0]["orden_puntaje"]
            df_form = df_fil[df_fil["cuil"].isin(ordp)]
            df_form["ORDEN"] = df_form["cuil"].apply(lambda x: ordp.index(x)+1)
            df_form["BONIFICACIÓN"] = df_form["cuil"].apply(lambda x: x in bon)
            anexos.append(df_form)

        if anexos:
            df_anexo = pd.concat(anexos).sort_values("ORDEN")
            df_anexo = df_anexo.rename(columns={
                "apellido_nombre":"APELLIDO Y NOMBRE",
                "formulario":"NIVEL",
                "calificacion":"CALIFICACIÓN"
            })[["APELLIDO Y NOMBRE","cuil","NIVEL","CALIFICACIÓN","ORDEN","BONIFICACIÓN"]]

            os.makedirs("tmp_anexos", exist_ok=True)
            generar_anexo_ii_docx(df_anexo, "tmp_anexos/anexo_ii.docx")
            with open("tmp_anexos/anexo_ii.docx","rb") as f:
                st.download_button("Descargar ANEXO II en Word", f, file_name="anexo_ii.docx")

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
            st.download_button("Descargar ANEXO III en Word", f, file_name="anexo_iii.docx")
