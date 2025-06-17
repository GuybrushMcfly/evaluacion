import streamlit as st
import pandas as pd
import io
import pdfkit
import os

def mostrar(supabase):
    st.set_page_config(page_title="Evaluación de Desempeño", layout="wide")  # debe ir al inicio si este es el script principal

    st.markdown("<h1 style='font-size:24px;'>📘 Análisis de Capacitación</h1>", unsafe_allow_html=True)

    # ---------- SECCIÓN 1: Tabla resumen individual por agente ----------
    evaluaciones = supabase.table("evaluaciones").select("*").execute().data
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data

    if not evaluaciones:
        st.info("No hay evaluaciones registradas.")
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

    # ---------- SECCIÓN 2: Anexos ----------
    st.markdown("## 📄 Generación de Anexos")

    df_filtrado = pd.DataFrame(evaluaciones)
    resumen = df_filtrado.groupby("formulario").agg(
        evaluados_total=("cuil", "count"),
        destacados_total=("calificacion", lambda x: (pd.Series(x) == "Destacado").sum())
    ).reset_index()
    resumen["cupo_maximo_30"] = (resumen["evaluados_total"] * 0.3).round().astype(int)

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

        html_ii = f"""
        <html><head><style>
        body {{ font-family: Arial; font-size: 12pt; margin: 40px; }}
        h2 {{ text-align: center; text-transform: uppercase; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid black; padding: 6px; text-align: left; }}
        </style></head><body>
        <h2>ANEXO II - LISTADO DE APOYO PARA BONIFICACIÓN POR DESEMPEÑO DESTACADO</h2>
        {listado.to_html(index=False, border=0)}
        </body></html>
        """

        os.makedirs("tmp_anexos", exist_ok=True)
        path_html = "tmp_anexos/anexo_ii.html"
        path_pdf = "tmp_anexos/anexo_ii.pdf"
        with open(path_html, "w", encoding="utf-8") as f:
            f.write(html_ii)

        pdfkit.from_file(path_html, path_pdf)
        with open(path_pdf, "rb") as f:
            st.download_button("⬇️ Descargar ANEXO II en PDF", f, file_name="anexo_ii.pdf", mime="application/pdf")

    if st.button("📝 Generar ANEXO III - Acta de Veeduría"):
        total_eval = df_filtrado.shape[0]
        total_dest = (df_filtrado["calificacion"] == "Destacado").sum()

        acta_texto = f"""
ACTA DE VEEDURÍA GREMIAL

En la dependencia seleccionada, con un total de {total_eval} personas evaluadas, se asignó la bonificación por desempeño destacado a {total_dest} agentes, de acuerdo al cupo máximo permitido del 30% según la normativa vigente.

La veeduría gremial constató que el procedimiento se realizó conforme a la normativa, y se firmó en señal de conformidad.

Fecha: ........................................................

Firmas:
- Representante de la unidad de análisis
- Veedor/a gremial
"""

        html_iii = f"""
        <html><head><style>
        body {{ font-family: Arial; font-size: 12pt; margin: 40px; }}
        h2 {{ text-align: center; text-transform: uppercase; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
        </style></head><body>
        <h2>ANEXO III - ACTA DE VEEDURÍA GREMIAL</h2>
        <pre>{acta_texto.strip()}</pre>
        </body></html>
        """

        path_html = "tmp_anexos/anexo_iii.html"
        path_pdf = "tmp_anexos/anexo_iii.pdf"
        with open(path_html, "w", encoding="utf-8") as f:
            f.write(html_iii)

        pdfkit.from_file(path_html, path_pdf)
        with open(path_pdf, "rb") as f:
            st.download_button("⬇️ Descargar ANEXO III en PDF", f, file_name="anexo_iii.pdf", mime="application/pdf")
