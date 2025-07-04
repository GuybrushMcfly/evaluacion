import streamlit as st
import pandas as pd
import io

def mostrar_listado_general(df_evals, agentes):
    st.markdown("### 📑 Listado General de Evaluaciones")


    # Selector de dependencia general
    opciones_dependencias = sorted(df_evals["dependencia_general"].dropna().unique().tolist())
    opciones_dependencias.insert(0, "TODAS")
    dependencia_seleccionada = st.selectbox("📂 Seleccioná una Dirección General", opciones_dependencias)

    if dependencia_seleccionada == "TODAS":
        df_filtrada = df_evals[df_evals["anulada"] != True].copy()
    else:
        df_filtrada = df_evals[(df_evals["anulada"] != True) & (df_evals["dependencia_general"] == dependencia_seleccionada)]

    df_agentes = pd.DataFrame(agentes)
    mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    filas_tabla = []
    filas_excel = []

    for e in df_filtrada.to_dict(orient="records"):
        cuil = e.get("cuil", "")
        agente = mapa_agentes.get(cuil, "Desconocido")
        formulario = e.get("formulario", "")
        calificacion = e.get("calificacion", "")
        total = e.get("puntaje_total", "")
        fecha_eval = e.get("fecha_evaluacion")

        if fecha_eval:
            try:
                fecha = pd.to_datetime(fecha_eval, utc=True).tz_convert("America/Argentina/Buenos_Aires")
                fecha_str = fecha.strftime("%d/%m/%Y %H:%M")
            except Exception:
                fecha_str = ""
        else:
            fecha_str = ""

        filas_tabla.append({
            "DEPENDENCIA GENERAL": e.get("dependencia_general", ""),
            "AGENTE": agente,
            "FORMULARIO": formulario,
            "CALIFICACI\u00d3N": calificacion,
            "FECHA": fecha_str
        })

        resumen_puntaje = ", ".join([f"{k} ({v})" for k, v in e.get("factor_puntaje", {}).items()])
        resumen_posicion = ", ".join([f"{k} ({v})" for k, v in e.get("factor_posicion", {}).items()])

        filas_excel.append({
            "CUIL": cuil,
            "AGENTE": agente,
            "FORMULARIO": formulario,
            "FACTOR/PUNTAJE": resumen_puntaje,
            "FACTOR/POSICION": resumen_posicion,
            "CALIFICACI\u00d3N": calificacion,
            "PUNTAJE TOTAL": total,
            "PUNTAJE M\u00c1XIMO": e.get("puntaje_maximo", ""),
            "PUNTAJE RELATIVO": e.get("puntaje_relativo", ""),
            "DEPENDENCIA": e.get("dependencia", ""),
            "DEPENDENCIA GENERAL": e.get("dependencia_general", "")
        })

    df_tabla = pd.DataFrame(filas_tabla)
    st.dataframe(df_tabla.sort_values("FECHA", ascending=False), use_container_width=True)

    df_excel = pd.DataFrame(filas_excel).sort_values(["DEPENDENCIA GENERAL", "FORMULARIO", "AGENTE"])
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_excel.to_excel(writer, index=False, sheet_name="Resumen")
    st.download_button(
        label="\ud83d\udcc5 Descargar Listado General (Excel)",
        data=buffer.getvalue(),
        file_name="listado_general.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
