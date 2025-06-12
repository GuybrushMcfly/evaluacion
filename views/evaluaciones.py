import streamlit as st
import pandas as pd
from pytz import timezone
import io

# ---- Vista: Evaluaciones ----
def mostrar_vista(supabase):
    st.header("📋 Evaluaciones realizadas")

    # Obtener evaluaciones y agentes
    evaluaciones = supabase.table("evaluaciones").select("*").execute().data
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data
    mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    if not evaluaciones:
        st.info("No hay evaluaciones registradas.")
        return

    # Construir resumen
    filas = []
    for e in evaluaciones:
        cuil = e["cuil"]
        agente = mapa_agentes.get(cuil, "Desconocido")
        formulario = e.get("formulario", "")

        # FACTOR PUNTAJE
        factores_puntaje = e.get("factor_puntaje", {})
        factores_formateados = {f"Factor {k.split('. ')[0].strip()}": v for k, v in factores_puntaje.items()}
        resumen_puntaje = ", ".join([f"{k} ({v})" for k, v in factores_formateados.items()])

        # FACTOR POSICION
        factores_posicion = e.get("factor_posicion", {})
        posiciones_formateadas = {f"Factor {k.split('. ')[0].strip()}": v for k, v in factores_posicion.items()}
        resumen_posicion = ", ".join([f"{k} ({v})" for k, v in posiciones_formateadas.items()])

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

    df_resumen = pd.DataFrame(filas)
    st.dataframe(df_resumen, use_container_width=True)

    # Botón de descarga
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_resumen.to_excel(writer, index=False, sheet_name='Evaluaciones')

    st.download_button(
        label="📥 Descargar en Excel",
        data=buffer.getvalue(),
        file_name="evaluaciones.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Anulación
    st.markdown("---")
    st.subheader("📌 Anular evaluaciones realizadas")
    hora_arg = timezone('America/Argentina/Buenos_Aires')

    df_eval = pd.DataFrame(evaluaciones)
    df_eval["Fecha"] = pd.to_datetime(df_eval["fecha_evaluacion"], utc=True).dt.tz_convert(hora_arg)
    df_eval["Fecha_formateada"] = df_eval["Fecha"].dt.strftime('%d/%m/%Y %H:%M')
    df_eval["anulada"] = df_eval["anulada"].fillna(False)
    df_eval["Estado"] = df_eval["anulada"].apply(lambda x: "Anulada" if x else "Registrada")

    columnas_visibles = [
        "Seleccionar", "apellido_nombre", "nivel", "formulario",
        "calificacion", "puntaje_total", "evaluador", "Fecha_formateada", "Estado"
    ]
    renombrar_columnas = {
        "Seleccionar": "Seleccionar",
        "apellido_nombre": "Apellido y Nombres",
        "nivel": "Nivel",
        "formulario": "Form.",
        "calificacion": "Calificación",
        "puntaje_total": "Puntaje",
        "evaluador": "Evaluador",
        "Fecha_formateada": "Fecha",
        "Estado": "Estado"
    }

    # ---- BLOQUE DE NO ANULADAS ----
    df_no_anuladas = df_eval[df_eval["anulada"] == False].copy()
    if not df_no_anuladas.empty:
        st.subheader("🔄 Evaluaciones que pueden anularse:")
        df_no_anuladas["Seleccionar"] = False
        df_no_anuladas = df_no_anuladas[[
            "Seleccionar", "id_evaluacion", "cuil", "apellido_nombre", "nivel",
            "formulario", "calificacion", "puntaje_total", "evaluador", "Fecha_formateada", "Estado"
        ]]

        df_para_mostrar = df_no_anuladas[[
            "Seleccionar", "apellido_nombre", "nivel", "formulario",
            "calificacion", "puntaje_total", "evaluador", "Fecha_formateada", "Estado"
        ]].rename(columns=renombrar_columnas)

        seleccion = st.data_editor(
            df_para_mostrar,
            use_container_width=True,
            hide_index=True,
            disabled=columnas_visibles[1:],
            column_config={"Seleccionar": st.column_config.CheckboxColumn("Seleccionar")}
        )

        if st.button("❌ Anular seleccionadas"):
            indices = seleccion[seleccion["Seleccionar"]].reset_index().index
            if len(indices) == 0:
                st.warning("⚠️ No hay evaluaciones seleccionadas para anular.")
            else:
                df_no_anuladas.reset_index(drop=True, inplace=True)
                for idx in indices:
                    eval_sel = df_no_anuladas.iloc[idx]
                    supabase.table("evaluaciones").update({"anulada": True})\
                        .eq("id_evaluacion", eval_sel["id_evaluacion"]).execute()
                    supabase.table("agentes").update({"evaluado_2025": False})\
                        .eq("cuil", str(eval_sel["cuil"]).strip()).execute()
                st.success(f"✅ {len(indices)} evaluaciones anuladas.")
                st.rerun()

    # ---- BLOQUE DE ANULADAS ----
    df_anuladas = df_eval[df_eval["anulada"]].copy()
    if not df_anuladas.empty:
        st.subheader("❌ Evaluaciones ya anuladas:")
        st.dataframe(
            df_anuladas[[
                "apellido_nombre", "nivel", "formulario",
                "calificacion", "puntaje_total", "evaluador",
                "Fecha_formateada", "Estado"
            ]].rename(columns={k: v for k, v in renombrar_columnas.items() if k != "Seleccionar"}),
            use_container_width=True,
            hide_index=True
        )
