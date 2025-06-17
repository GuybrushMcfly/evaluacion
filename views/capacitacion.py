import streamlit as st
import pandas as pd
import io

def mostrar(supabase):
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

    # ---------- SECCIÓN 2: Análisis por Dependencia General ----------
    st.markdown("## 📊 Análisis por Dependencia General (Criterios de Tramo)")

    unidades = supabase.table("unidades_evaluacion").select("*").execute().data
    if not evaluaciones or not unidades:
        st.warning("No hay datos de evaluaciones o unidades de evaluación disponibles.")
        return

    df_eval = pd.DataFrame(evaluaciones)
    df_unidades = pd.DataFrame(unidades)

    df_eval = df_eval[(df_eval["activo"] == True) & (df_eval["anulada"] != True)]

    residuales = df_unidades[df_unidades["residual"] == True]["unidad_analisis"].unique()
    df_eval["residual_general"] = df_eval["unidad_analisis"].isin(residuales)

    dependencias = sorted(df_eval["dependencia_general"].dropna().unique().tolist())
    dependencias.append("RESIDUAL GENERAL")

    seleccion = st.selectbox("Seleccioná una Dependencia General", dependencias)

    if seleccion == "RESIDUAL GENERAL":
        df_filtrado = df_eval[df_eval["residual_general"] == True]
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
