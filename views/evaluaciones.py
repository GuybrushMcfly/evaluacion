import streamlit as st
import pandas as pd
import io

def mostrar(supabase):
    st.header("📋 Evaluaciones realizadas")

    evaluaciones = supabase.table("evaluaciones").select("*").execute().data
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data
    mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    if not evaluaciones:
        st.info("No hay evaluaciones registradas.")
        return

    filas = []
    for e in evaluaciones:
        cuil = e["cuil"]
        agente = mapa_agentes.get(cuil, "Desconocido")
        formulario = e.get("formulario", "")

        factores_puntaje = e.get("factor_puntaje", {})
        resumen_puntaje = ", ".join([f"{k} ({v})" for k, v in factores_puntaje.items()])

        factores_posicion = e.get("factor_posicion", {})
        resumen_posicion = ", ".join([f"{k} ({v})" for k, v in factores_posicion.items()])

        filas.append({
            "CUIL": cuil,
            "AGENTE": agente,
            "FORMULARIO": formulario,
            "FACTOR/POSICION": resumen_posicion,
            "FACTOR/PUNTAJE": resumen_puntaje,
            "CALIFICACION": e.get("calificacion", ""),
            "PUNTAJE TOTAL": e.get("puntaje_total", ""),
            "PUNTAJE MÁXIMO": e.get("puntaje_maximo", ""),
            "PUNTAJE RELATIVO": e.get("puntaje_relativo", "")
        })

    df = pd.DataFrame(filas)
    st.dataframe(df, use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Evaluaciones')

    st.download_button(
        label="📥 Descargar en Excel",
        data=buffer.getvalue(),
        file_name="evaluaciones.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
