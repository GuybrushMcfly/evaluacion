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

    # Limpia campos numéricos de NaN o None
    for key in ["anio_evaluacion", "evaluados_total", "destacados_total", "cupo_maximo_30"]:
        val = r.get(key)
        if val is None or (isinstance(val, float) and math.isnan(val)):
            r[key] = 0

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

    evaluaciones = supabase.table("evaluaciones").select("*").execute().data
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data
    unidades = supabase.table("unidades_evaluacion").select("*").execute().data
    analisis_previos = supabase.table("analisis_evaluaciones").select("*").execute().data

    if not evaluaciones or not unidades:
        st.warning("No hay datos disponibles.")
        return

    evaluaciones = [e for e in evaluaciones if not e.get("anulada", False)]
    mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    # ---- SECCION 1: EXCEL ----
    filas_tabla = []
    filas_excel = []
    for e in evaluaciones:
        cuil = e.get("cuil", "")
        agente = mapa_agentes.get(cuil, "Desconocido")
        formulario = e.get("formulario", "")
        calificacion = e.get("calificacion", "")
        total = e.get("puntaje_total", "")
        factores_puntaje = e.get("factor_puntaje") or {}
        resumen_puntaje = ", ".join([f"{k} ({v})" for k, v in factores_puntaje.items()])

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
            "FACTOR/PUNTAJE": resumen_puntaje,
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
        df_unidades = pd.DataFrame(unidades)
        residuales = df_unidades[df_unidades["residual"] == True]["unidad_analisis"].unique()
        df = df[df["activo"] == True]
        df["residual_general"] = df["unidad_analisis"].isin(residuales)

        agrupados = df.groupby(["unidad_analisis", "unidad_evaluadora", "formulario"])
        registros = []
        for (ua, ue, f), grupo in agrupados:
            evaluados_total = len(grupo)
            destacados_total = grupo["calificacion"].eq("Destacado").sum()
            cupo = round(evaluados_total * 0.3)
            ordenados = grupo.sort_values("puntaje_relativo", ascending=False)
            orden_puntaje = ordenados["cuil"].tolist()
            bonificados = orden_puntaje[:int(cupo)]

            anio_vals = grupo["anio_evaluacion"].dropna().astype(int)
            anio_eval = int(anio_vals.max()) if not anio_vals.empty else 0

            registro = {
                "unidad_analisis": ua,
                "unidad_evaluadora": ue,
                "formulario": f,
                "anio_evaluacion": anio_eval,
                "evaluados_total": evaluados_total,
                "destacados_total": destacados_total,
                "cupo_maximo_30": int(cupo),
                "bonificados_cuils": bonificados,
                "orden_puntaje": orden_puntaje,
                "fecha_analisis": datetime.now().isoformat()
            }

            # Limpiar registro para evitar errores JSON
            registro = limpiar_registro(registro)

            registros.append(registro)

        # Limpiar registros previos para evitar duplicados
        supabase.table("analisis_evaluaciones").delete().neq("unidad_analisis", "").execute()

        # Insertar registros limpios
        for r in registros:
            st.write("Insertando registro:", r)  # Opcional: para debug
            supabase.table("analisis_evaluaciones").insert(r).execute()

        st.success("Análisis guardado en la tabla analisis_evaluaciones.")

    # ---- SECCION 3: ANEXOS ----
    df_eval = pd.DataFrame(evaluaciones)
    df_unidades = pd.DataFrame(unidades)
    df_analisis = pd.DataFrame(analisis_previos)
    df_eval = df_eval[df_eval["activo"] == True]
    residuales = df_unidades[df_unidades["residual"] == True]["unidad_analisis"].unique()
    df_eval["residual_general"] = df_eval["unidad_analisis"].isin(residuales)

    opciones = sorted(df_eval["dependencia_general"].dropna().unique().tolist())
    opciones.append("RESIDUAL GENERAL")
    seleccion = st.selectbox("Seleccioná una Dirección General", opciones)

    if seleccion == "RESIDUAL GENERAL":
        df_filtrado = df_eval[df_eval["residual_general"]]
    else:
        df_filtrado = df_eval[df_eval["dependencia_general"] == seleccion]

    if df_filtrado.empty:
        st.info("No hay evaluaciones para esta dependencia.")
        return

    resumen = df_filtrado.groupby("formulario").agg(
        evaluados_total=("cuil", "count"),
        destacados_total=("calificacion", lambda x: (pd.Series(x) == "Destacado").sum())
    ).reset_index()
    resumen["cupo_maximo_30"] = (resumen["evaluados_total"] * 0.3).round().astype(int)
    st.dataframe(resumen)

    if st.button("Generar ANEXO II - Listado de Apoyo"):
        anexos = []
        for formulario in df_filtrado["formulario"].unique():
            ua = df_filtrado["unidad_analisis"].iloc[0]
            analisis = df_analisis[(df_analisis["unidad_analisis"] == ua) & (df_analisis["formulario"] == formulario)]
            if not analisis.empty:
                bonificados = analisis.iloc[0]["bonificados_cuils"]
                orden = analisis.iloc[0]["orden_puntaje"]
                df_form = df_filtrado[df_filtrado["formulario"] == formulario]
                df_form = df_form[df_form["cuil"].isin(orden)]
                df_form["ORDEN"] = df_form["cuil"].apply(lambda x: orden.index(x) + 1)
                df_form["BONIFICACIÓN"] = df_form["cuil"].apply(lambda x: x in bonificados)
                anexos.append(df_form)

        if anexos:
            df_anexo = pd.concat(anexos)
            df_anexo = df_anexo.sort_values("ORDEN")
            df_anexo = df_anexo.rename(columns={
                "apellido_nombre": "APELLIDO Y NOMBRE",
                "formulario": "NIVEL",
                "calificacion": "CALIFICACIÓN"
            })[["APELLIDO Y NOMBRE", "cuil", "NIVEL", "CALIFICACIÓN", "ORDEN", "BONIFICACIÓN"]]

            os.makedirs("tmp_anexos", exist_ok=True)
            generar_anexo_ii_docx(df_anexo, "tmp_anexos/anexo_ii.docx")
            with open("tmp_anexos/anexo_ii.docx", "rb") as f:
                st.download_button("Descargar ANEXO II en Word", f, file_name="anexo_ii.docx")

    if st.button("Generar ANEXO III - Acta de Veeduría"):
        total_eval = df_filtrado.shape[0]
        total_dest = (df_filtrado["calificacion"] == "Destacado").sum()

        acta_texto = f"""ACTA DE VEEDURÍA GREMIAL

En la dependencia {seleccion}, con un total de {total_eval} personas evaluadas, se asignó la bonificación por desempeño destacado a {total_dest} agentes, de acuerdo al cupo máximo permitido del 30% según la normativa vigente.

La veeduría gremial constató que el procedimiento se realizó conforme a la normativa, y se firmó en señal de conformidad.

Fecha: ........................................................

Firmas:
- Representante de la unidad de análisis
- Veedor/a gremial"""

        generar_anexo_iii_docx(acta_texto, "tmp_anexos/anexo_iii.docx")
        with open("tmp_anexos/anexo_iii.docx", "rb") as f:
            st.download_button("Descargar ANEXO III en Word", f, file_name="anexo_iii.docx")
