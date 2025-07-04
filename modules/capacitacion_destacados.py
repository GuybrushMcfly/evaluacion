import streamlit as st
import pandas as pd
import io
import math

def mostrar_destacados(df_evals, agentes):
    st.markdown("### 🌟 Cupo DESTACADOS por Dependencia General")

    # --- Preparar dataframes
    df_agentes = pd.DataFrame(agentes)
    #   df_agentes = df_agentes[df_agentes["activo"] == True]

    df_eval_validas = df_evals[
        (df_evals["calificacion"] == "DESTACADO") & (df_evals["anulada"] != True)
    ]

    # --- Agrupar por dependencia
    resumen = df_agentes.groupby("dependencia_general").agg(
        total_agentes=("cuil", "count")
    ).reset_index()
    resumen["cupo_destacados"] = resumen["total_agentes"].apply(lambda x: math.floor(x * 0.3) if (x * 0.3) - math.floor(x * 0.3) <= 0.5 else math.floor(x * 0.3) + 1)
    evaluados_destacados = df_eval_validas.groupby("dependencia_general").agg(
        evaluados_con_destacado=("cuil", "count")
    ).reset_index()

    resumen = pd.merge(resumen, evaluados_destacados, on="dependencia_general", how="left")
    resumen["evaluados_con_destacado"] = resumen["evaluados_con_destacado"].fillna(0).astype(int)

    # --- Estado visual
    def calcular_estado(row):
        if row["evaluados_con_destacado"] == 0:
            return "🟡"
        elif row["evaluados_con_destacado"] <= row["cupo_destacados"]:
            return "🟢"
        else:
            return "🔴"

    resumen["Estado"] = resumen.apply(calcular_estado, axis=1)

    # --- Mostrar tabla
    st.dataframe(
        resumen.rename(columns={
            "dependencia_general": "DEPENDENCIA GENERAL",
            "total_agentes": "AGENTES",
            "cupo_destacados": "CUPO (30%)",
            "evaluados_con_destacado": "EVALUADOS"
        }),
        use_container_width=True,
        hide_index=True
    )


    # --- Descargar Excel para DESTACADOS
    df_destacados_excel = resumen.copy()
    # Convertir emojis a texto para Excel
    def estado_texto(row):
        if row["evaluados_con_destacado"] == 0:
            return "SIN EVALUACIONES"
        elif row["evaluados_con_destacado"] <= row["cupo_destacados"]:
            return "DENTRO DEL CUPO"
        else:
            return "EXCEDE CUPO"
    
    df_destacados_excel["Estado_Excel"] = df_destacados_excel.apply(estado_texto, axis=1)
    df_destacados_excel = df_destacados_excel.drop("Estado", axis=1)
    df_destacados_excel = df_destacados_excel.rename(columns={"Estado_Excel": "ESTADO"})
    
    buffer_destacados = io.BytesIO()
    with pd.ExcelWriter(buffer_destacados, engine="xlsxwriter") as writer:
        df_destacados_excel.to_excel(writer, index=False, sheet_name="Destacados")
    st.download_button(
        label="📥 Descargar Cupo DESTACADOS (Excel)",
        data=buffer_destacados.getvalue(),
        file_name="cupo_destacados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- Métricas globales
    total_agentes = resumen["total_agentes"].sum()
    total_cupo = resumen["cupo_destacados"].sum()
    total_usados = resumen["evaluados_con_destacado"].sum()

    st.markdown("### 📊 Indicadores")
    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Total de Agentes", total_agentes)
    col2.metric("🏅 Cupo total de DESTACADOS", total_cupo)
    col3.metric("✅ DESTACADOS Asignados", total_usados)


