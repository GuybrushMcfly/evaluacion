import streamlit as st
from datetime import datetime
import pandas as pd
import secrets
import bcrypt

def mostrar(supabase):
    st.markdown("<h1 style='font-size:26px;'>⚙️ Configuración del Sistema</h1>", unsafe_allow_html=True)

    # --- CONSULTA CONFIGURACIÓN ACTUAL ---
    config_items = supabase.table("configuracion").select("*").execute().data
    config_map = {item["id"]: item for item in config_items}

    # Crear tabla de configuración editable
    df_config = pd.DataFrame([
        {
            "ID": "formulario_activo",
            "Descripción": "📝 Formulario habilitado",
            "Activo": config_map.get("formulario_activo", {}).get("valor", True)
        },
        {
            "ID": "anulacion_activa",
            "Descripción": "❌ Permitir anulación de evaluaciones",
            "Activo": config_map.get("anulacion_activa", {}).get("valor", True)
        }
    ])

   # st.markdown("### 🔧 Parámetros del sistema")
    st.markdown("<h2 style='font-size:20px;'>🔧 Parámetros del sistema</h2>", unsafe_allow_html=True)

    
    edit_config = st.data_editor(
        df_config[["Descripción", "Activo"]],
        use_container_width=True,
        hide_index=True,
        disabled=["Descripción"],
        column_config={"Activo": st.column_config.CheckboxColumn("Activo")}
    )

    if st.button("💾 Guardar cambios", use_container_width=True):
        usuario = st.session_state.get("usuario", "desconocido")
        for i, row in edit_config.iterrows():
            id_config = df_config.loc[i, "ID"]
            nuevo_valor = row["Activo"]
            supabase.table("configuracion").upsert({
                "id": id_config,
                "valor": nuevo_valor,
                "actualizado_por": usuario
            }).execute()
        st.success("✅ Configuración actualizada correctamente.")
        st.rerun()

    st.divider()

    # --- EDICIÓN DE EVALUADOR POR AGENTE ---
    st.markdown("<h2 style='font-size:20px;'>👥 Asignación de Evaluadores</h2>", unsafe_allow_html=True)

    #st.markdown("### 👥 Asignación de Evaluadores")

    # --- Cargar datos ---
    agentes_data = supabase.table("agentes").select("cuil, apellido_nombre, dependencia, evaluador_2024").execute().data
    usuarios_data = supabase.table("usuarios").select("usuario, apellido_nombre, dependencia, dependencia_general, activo").execute().data

    if not agentes_data or not usuarios_data:
        st.warning("⚠️ No hay datos disponibles.")
        return

    mapa_agentes = {a["apellido_nombre"]: a for a in agentes_data}
    mapa_usuarios = {u["usuario"]: u for u in usuarios_data if u["activo"]}

    lista_agentes = ["- Seleccioná a un agente -"] + list(mapa_agentes.keys())
    nombre_seleccionado = st.selectbox("👤 Agente a modificar", lista_agentes)

    if nombre_seleccionado == "- Seleccioná a un agente -":
        st.info("Por favor, seleccioná un agente para modificar.")
        return

    # --- Continuar con selección válida ---
    agente = mapa_agentes[nombre_seleccionado]

    dependencias_disponibles = sorted({u["dependencia"] for u in usuarios_data if u["activo"] and u["dependencia"]})
    nueva_dependencia = st.selectbox(
        "🏢 Nueva dependencia",
        dependencias_disponibles,
        index=dependencias_disponibles.index(agente.get("dependencia", ""))
    )

    evaluadores_opciones = [u for u in usuarios_data if u["dependencia"] == nueva_dependencia and u["activo"]]
    opciones_evaluador = {u["apellido_nombre"]: u["usuario"] for u in evaluadores_opciones}

    usuario_actual = agente.get("evaluador_2024", "")
    nombre_actual = next((u["apellido_nombre"] for u in usuarios_data if u["usuario"] == usuario_actual), "[No asignado]")

    nombre_evaluador = st.selectbox(
        "🧑‍🏫 Evaluador asignado (2024)",
        list(opciones_evaluador.keys()),
        index=0 if nombre_actual not in opciones_evaluador else list(opciones_evaluador.keys()).index(nombre_actual)
    )

    if st.button("🔁 Actualizar asignación", use_container_width=True):
        nuevo_usuario = opciones_evaluador[nombre_evaluador]
        dependencia_gral = mapa_usuarios[nuevo_usuario]["dependencia_general"]
        supabase.table("agentes").update({
            "dependencia": nueva_dependencia,
            "dependencia_general": dependencia_gral,
            "evaluador_2024": nuevo_usuario
        }).eq("cuil", agente["cuil"]).execute()
        st.success("✅ Datos actualizados correctamente.")



    st.divider()
    #st.markdown("### 🔐 Generar contraseña para evaluador")
    st.markdown("<h2 style='font-size:20px;'>🔐 Generar contraseña para evaluador</h2>", unsafe_allow_html=True)

    
    # Listado de evaluadores activos
    evaluadores_disponibles = {u["apellido_nombre"]: u for u in usuarios_data if u["activo"]}
    opciones_nombres = ["- Seleccioná a un evaluador -"] + sorted(evaluadores_disponibles.keys())
    
    nombre_seleccionado_pwd = st.selectbox("👤 Seleccioná al evaluador", opciones_nombres, index=0)
    
    if nombre_seleccionado_pwd != "- Seleccioná a un evaluador -":
        if st.button("🔐 Generar contraseña", use_container_width=True):
            usuario_seleccionado = evaluadores_disponibles[nombre_seleccionado_pwd]
            nuevo_usuario = usuario_seleccionado["usuario"]
    
            # Generar clave aleatoria de 5 dígitos
            nueva_password = str(secrets.randbelow(10**5)).zfill(5)  # Siempre 5 dígitos
            hashed = bcrypt.hashpw(nueva_password.encode(), bcrypt.gensalt()).decode()
    
            # Guardar en Supabase
            supabase.table("usuarios").update({
                "password": hashed,
                "cambiar_password": True
            }).eq("usuario", nuevo_usuario).execute()
    
            # Mostrar usuario y clave
            st.success(f"""
            ✅ Contraseña generada correctamente:
    
            - **Usuario**: `{nuevo_usuario}`  
            - **Contraseña temporal**: `{nueva_password}`
            """)

