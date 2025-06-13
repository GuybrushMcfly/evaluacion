import streamlit as st
import pandas as pd
from pytz import timezone
import time

# ---- Vista: Evaluaciones ----
def mostrar(supabase):
    st.header("📋 Evaluaciones realizadas")

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

    # ----------------------
    # RESUMEN DE INDICADORES
    # ----------------------
    df_vigente = df_eval[df_eval["anulada"] == False].copy()
    total = len(df_eval)
    evaluadas = len(df_vigente)
    porcentaje = (evaluadas / total * 100) if total else 0

    st.markdown("### 📊 Indicadores")
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Total para evaluar", total)
    with col2: st.metric("Total evaluados", evaluadas)
    with col3: st.metric("% Evaluados", f"{porcentaje:.1f}%")

    st.progress(min(100, int(porcentaje)), text=f"Progreso de evaluaciones registradas: {porcentaje:.1f}%")

    # ----------------------
    # DETALLE USO DE FORMULARIOS
    # ----------------------
    st.markdown("### 📑 Uso de formularios")
    uso_formularios = df_vigente["formulario"].value_counts().sort_index()
    st.dataframe(uso_formularios.rename_axis("Formulario").reset_index(name="Cantidad"), use_container_width=True, hide_index=True)

    # ----------------------
    # DETALLE POR CALIFICACIÓN
    # ----------------------
    st.markdown("### 🏷️ Distribución por calificación")
    categorias = ["DESTACADO", "BUENO", "REGULAR", "DEFICIENTE"]
    df_vigente["calificacion"] = df_vigente["calificacion"].fillna("SIN DATOS")
    calif = df_vigente["calificacion"].value_counts().reindex(categorias, fill_value=0)
    st.dataframe(calif.rename_axis("Calificación").reset_index(name="Cantidad"), use_container_width=True, hide_index=True)

    # ----------------------
    # BLOQUE DE NO ANULADAS
    # ----------------------
    columnas_visibles = [
        "Seleccionar", "apellido_nombre", "formulario",
        "calificacion", "puntaje_total", "evaluador", "Fecha_formateada", "Estado"
    ]
    renombrar_columnas = {
        "Seleccionar": "Seleccionar",
        "apellido_nombre": "Apellido y Nombres",
        "formulario": "Form.",
        "calificacion": "Calificación",
        "puntaje_total": "Puntaje",
        "evaluador": "Evaluador",
        "Fecha_formateada": "Fecha",
        "Estado": "Estado"
    }

    df_no_anuladas = df_eval[df_eval["anulada"] == False].copy()
    if not df_no_anuladas.empty:
        st.subheader("🔄 Evaluaciones que pueden anularse:")
        df_no_anuladas["Seleccionar"] = False
        df_no_anuladas = df_no_anuladas[[
            "Seleccionar", "id_evaluacion", "cuil", "apellido_nombre",
            "formulario", "calificacion", "puntaje_total", "evaluador", "Fecha_formateada", "Estado"
        ]]

        df_para_mostrar = df_no_anuladas[[
            "Seleccionar", "apellido_nombre", "formulario",
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
                    supabase.table("agentes").update({"evaluado_2024": False})\
                        .eq("cuil", str(eval_sel["cuil"]).strip()).execute()
                st.success(f"✅ {len(indices)} evaluaciones anuladas.")
                time.sleep(2)
                st.rerun()

    # ----------------------
    # BLOQUE DE ANULADAS
    # ----------------------
    df_anuladas = df_eval[df_eval["anulada"]].copy()
    if not df_anuladas.empty:
        st.subheader("❌ Evaluaciones ya anuladas:")
        st.dataframe(
            df_anuladas[[
                "apellido_nombre", "formulario",
                "calificacion", "puntaje_total", "evaluador",
                "Fecha_formateada", "Estado"
            ]].rename(columns={k: v for k, v in renombrar_columnas.items() if k != "Seleccionar"}),
            use_container_width=True,
            hide_index=True
        )
