import streamlit as st
import pandas as pd
import io

def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>📘 Análisis de Capacitación</h1>", unsafe_allow_html=True)

    # Traer evaluaciones
    evaluaciones = supabase.table("evaluaciones").select("*").execute().data
    if not evaluaciones:
        st.info("No hay evaluaciones registradas.")
        return

    # Traer agentes para obtener nombres
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data
    mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    # Armar tabla con resumen de factores/puntaje
    filas = []
    for e in evaluaciones:
        cuil = e.get("cuil")
        agente = mapa_agentes.get(cuil, "Desconocido")
        factores = e.get("factor_puntaje", {})
        resumen = ", ".join([f"{k} ({v})" for k, v in factores.items()])

        filas.append({
            "CUIL": cuil,
            "Agente": agente,
            "Factor/Puntaje": resumen
        })

    df = pd.DataFrame(filas)
    st.dataframe(df, use_container_width=True)

    # Botón para descargar en Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Resumen")
    st.download_button(
        label="📥 Descargar Excel",
        data=buffer.getvalue(),
        file_name="resumen_capacitacion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
