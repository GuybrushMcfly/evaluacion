import streamlit as st
import pandas as pd
from pytz import timezone

# ---- Vista: Evaluaciones ----
def mostrar(supabase):
    st.header("📋 Evaluaciones realizadas")

    # Aviso: resumen de factores está en otra sección
    st.info("📊 Para ver el resumen de factores y descargar en Excel, accedé a la sección 📘 Capacitación.")

    # Obtener evaluaciones
    evaluaciones = supabase.table("evaluaciones").select("*").execute().data
    if not evaluaciones:
        st.info("No hay evaluaciones registradas.")
        return

    # Configurar zona horaria y preparar dataframe
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
