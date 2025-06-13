import streamlit as st
import pandas as pd
import io

def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>📘 Análisis de Capacitación</h1>", unsafe_allow_html=True)

    # Obtener evaluaciones y agentes
    evaluaciones = supabase.table("evaluaciones").select("*").execute().data
    evaluaciones = [e for e in evaluaciones if not e.get("anulada", False)]
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data

    if not evaluaciones:
        st.info("No hay evaluaciones registradas.")
        return

    # Crear mapa de CUIL a nombre
    mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    # ---- Tabla visible simplificada ----
    filas_tabla = []
    filas_excel = []

    for e in evaluaciones:
        cuil = e.get("cuil", "")
        agente = mapa_agentes.get(cuil, "Desconocido")
        formulario = e.get("formulario", "")
        calificacion = e.get("calificacion", "")
        total = e.get("puntaje_total", "")

        # Para pantalla
        filas_tabla.append({
            "AGENTE": agente,
            "FORMULARIO": formulario,
            "CALIFICACION": calificacion,
            "TOTAL": total
        })

        # Para Excel
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

    # Mostrar tabla simple
    df_tabla = pd.DataFrame(filas_tabla)
    st.dataframe(df_tabla, use_container_width=True)

    # Generar Excel
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
