import streamlit as st
import pandas as pd
import io
import os
from docx import Document

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
    st.markdown("<h1 style='font-size:24px;'>📘 Análisis de Capacitación</h1>", unsafe_allow_html=True)

    evaluaciones = supabase.table("evaluaciones").select("*").execute().data
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data
    unidades = supabase.table("unidades_evaluacion").select("*").execute().data

    if not evaluaciones or not unidades:
        st.warning("No hay datos disponibles.")
        return

    evaluaciones = [e for e in evaluaciones if not e.get("anulada", False)]
    mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    filas_tabla = []
    filas_excel = []
    for e in evaluaciones:
        cuil = e.get("cuil", "")
        agente = mapa_agentes.get(cuil, "Desconocido")
        formulario = e.get("formulario", "")
        calificacion = e.get("calificacion", "")
        total = e.get("puntaje_total", "")

        filas_tabla.append({
            "AGENTE": agente,
            "FORMULARIO": formulario,
            "CALIFICACION": calificacion,
            "TOTAL": total
        })

        factores_puntaje = e.get("factor_puntaje", {})
        resumen_puntaje = ", ".join([f"{k} ({v})" for k, v in factores_puntaje.items()])
        factores_posicion = e.get("factor_posicion", {})
        resumen_posicion = ", ".join([f"{k} ({v})" for k, v in factores_posicion.items()])

        filas_excel.append({
            "CUIL": cuil,
            "AGENTE": agente,
            "FORMULARIO": formulario,
            "FACTOR/PUNTAJE": resumen_puntaje,
            "FACTOR/POSICION": resumen_posicion,
            "CALIFICACION": calificacion,
            "PUNTAJE TOTAL": total,
            "PUNTAJE MÁXIMO": e.get("puntaje_maximo", ""),
            "PUNTAJE RELATIVO": e.get("puntaje_relativo", ""),
            "DEPENDENCIA": e.get("dependencia", ""),
            "DEPENDENCIA GENERAL": e.get("dependencia_general", "")
        })

    st.markdown("### 📄 Resumen Individual")
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

    # ---------- SECCIÓN 2: Filtro por Dirección General ----------
    df_eval = pd.DataFrame(evaluaciones)
    df_unidades = pd.DataFrame(unidades)
    df_eval = df_eval[df_eval["activo"] == True]
    residuales = df_unidades[df_unidades["residual"] == True]["unidad_analisis"].unique()
    df_eval["residual_general"] = df_eval["unidad_analisis"].isin(residuales)

    opciones = sorted(df_eval["dependencia_general"].dropna().unique().tolist())
    opciones.append("RESIDUAL GENERAL")
    seleccion = st.selectbox("📂 Seleccioná una Dirección General", opciones)

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

    # ---------- SECCIÓN 3: Botones para ANEXO II y III ----------
    if st.button("📂 Generar ANEXO II - Listado de Apoyo"):
        df_ordenado = df_filtrado[df_filtrado["calificacion"] == "Destacado"]
        df_ordenado = df_ordenado.sort_values(by="puntaje_relativo", ascending=False)
        df_ordenado["ORDEN"] = range(1, len(df_ordenado) + 1)
        df_ordenado["BONIFICACIÓN"] = df_ordenado["ORDEN"] <= resumen["cupo_maximo_30"].sum()

        listado = df_ordenado[[
            "apellido_nombre", "cuil", "formulario", "calificacion", "ORDEN", "BONIFICACIÓN"
        ]].rename(columns={
            "apellido_nombre": "APELLIDO Y NOMBRE",
            "formulario": "NIVEL",
            "calificacion": "CALIFICACIÓN"
        })

        os.makedirs("tmp_anexos", exist_ok=True)
        generar_anexo_ii_docx(listado, "tmp_anexos/anexo_ii.docx")
        with open("tmp_anexos/anexo_ii.docx", "rb") as f:
            st.download_button("⬇️ Descargar ANEXO II en Word", f, file_name="anexo_ii.docx")

    if st.button("📝 Generar ANEXO III - Acta de Veeduría"):
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
            st.download_button("⬇️ Descargar ANEXO III en Word", f, file_name="anexo_iii.docx")
