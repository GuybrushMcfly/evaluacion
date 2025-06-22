import streamlit as st
from datetime import datetime
import pandas as pd

def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>⚙️ Configuración del Sistema</h1>", unsafe_allow_html=True)
    
    # --- Consultar configuración actual ---
    config_items = supabase.table("configuracion").select("*").execute().data
    config_map = {item["id"]: item for item in config_items}

    # Crear dataframe editable
    df_config = pd.DataFrame([
        {
            "ID": "formulario_activo",
            "Descripción": "Formulario habilitado",
            "Activo": config_map.get("formulario_activo", {}).get("valor", True)
        },
        {
            "ID": "anulacion_activa",
            "Descripción": "Permitir anulación de evaluaciones",
            "Activo": config_map.get("anulacion_activa", {}).get("valor", True)
        }
    ])
    
    # Mostrar tabla editable
    st.markdown("### 🔧 Parámetros del sistema")
    edit_config = st.data_editor(
        df_config[["Descripción", "Activo"]],
        use_container_width=True,
        hide_index=True,
        disabled=["Descripción"],
        column_config={
            "Activo": st.column_config.CheckboxColumn("Activo")
        }
    )
    
    # Botón para guardar
    if st.button("💾 Guardar cambios"):
        usuario = st.session_state.get("usuario", "desconocido")
        ahora = datetime.now().isoformat()
    
        for i, row in edit_config.iterrows():
            id_config = df_config.loc[i, "ID"]
            nuevo_valor = row["Activo"]
            supabase.table("configuracion").upsert({
                "id": id_config,
                "valor": nuevo_valor,
                "actualizado_por": usuario
            }).execute()
    
        st.success("✅ Configuración actualizada.")
        st.rerun()

    # --- A PARTIR DE ACÁ: Lógica de edición de agente ---
    agentes_data = supabase.table("agentes").select("cuil, apellido_nombre, dependencia, evaluador_2024").execute().data
    usuarios_data = supabase.table("usuarios").select("usuario, apellido_nombre, dependencia, dependencia_general, activo").execute().data

    if not agentes_data or not usuarios_data:
        st.warning("No hay datos disponibles.")
        return

    mapa_agentes = {a["apellido_nombre"]: a for a in agentes_data}
    mapa_usuarios = {u["usuario"]: u for u in usuarios_data if u["activo"]}

    nombre_seleccionado = st.selectbox("Seleccioná un agente", list(mapa_agentes.keys()))
    agente = mapa_agentes[nombre_seleccionado]

    dependencias_disponibles = sorted(set(u["dependencia"] for u in usuarios_data if u["activo"] and u["dependencia"]))
    nueva_dependencia = st.selectbox("Nueva dependencia", dependencias_disponibles, index=dependencias_disponibles.index(agente.get("dependencia", "")))

    evaluadores_opciones = [u for u in usuarios_data if u["dependencia"] == nueva_dependencia and u["activo"]]
    opciones_evaluador = {u["apellido_nombre"]: u["usuario"] for u in evaluadores_opciones}

    usuario_actual = agente.get("evaluador_2024", "")
    nombre_actual = next((u["apellido_nombre"] for u in usuarios_data if u["usuario"] == usuario_actual), "[No asignado]")

    nombre_evaluador = st.selectbox("Evaluador asignado (2024)", list(opciones_evaluador.keys()), index=0 if nombre_actual not in opciones_evaluador else list(opciones_evaluador.keys()).index(nombre_actual))

    if st.button("Actualizar datos"):
        nuevo_usuario = opciones_evaluador[nombre_evaluador]
        dependencia_gral = mapa_usuarios[nuevo_usuario]["dependencia_general"]

        supabase.table("agentes").update({
            "dependencia": nueva_dependencia,
            "dependencia_general": dependencia_gral,
            "evaluador_2024": nuevo_usuario
        }).eq("cuil", agente["cuil"]).execute()

        st.success("Datos actualizados correctamente.")
