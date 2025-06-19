import streamlit as st
from datetime import datetime

def mostrar(supabase):
    st.markdown("<h1 style='font-size:24px;'>⚙️ Configuración del Sistema</h1>", unsafe_allow_html=True)

    # Consultar configuración actual
    config_items = supabase.table("configuracion").select("*").execute().data
    config_map = {item["id"]: item for item in config_items}

    # Formulario activo
    formulario_activo = config_map.get("formulario_activo", {}).get("valor", True)
    nuevo_formulario_activo = st.checkbox("✅ Formulario habilitado", value=formulario_activo)

    # Anulación activa
    anulacion_activa = config_map.get("anulacion_activa", {}).get("valor", True)
    nueva_anulacion_activa = st.checkbox("❌ Permitir anulación de evaluaciones", value=anulacion_activa)

    if st.button("💾 Guardar cambios"):
        usuario = st.session_state.get("usuario", "desconocido")
        ahora = datetime.now().isoformat()

        # Actualizar cada configuración si cambió
        if nuevo_formulario_activo != formulario_activo:
            supabase.table("configuracion").upsert({
                "id": "formulario_activo",
                "valor": nuevo_formulario_activo,
                "actualizado_por": usuario,
            }).execute()

        if nueva_anulacion_activa != anulacion_activa:
            supabase.table("configuracion").upsert({
                "id": "anulacion_activa",
                "valor": nueva_anulacion_activa,
                "actualizado_por": usuario,
            }).execute()

        st.success("✅ Cambios guardados correctamente.")


# --- Datos desde Supabase ---
agentes_data = supabase.table("agentes").select("cuil, apellido_nombre, dependencia, evaluador_2024").execute().data
usuarios_data = supabase.table("usuarios").select("usuario, apellido_nombre, dependencia, dependencia_general, activo").execute().data

if not agentes_data or not usuarios_data:
    st.warning("No hay datos disponibles.")
else:
    # --- Crear mapas y listas ---
    mapa_agentes = {a["apellido_nombre"]: a for a in agentes_data}
    mapa_usuarios = {u["usuario"]: u for u in usuarios_data if u["activo"]}

    # --- Selector de agente ---
    nombre_seleccionado = st.selectbox("Seleccioná un agente", list(mapa_agentes.keys()))
    agente = mapa_agentes[nombre_seleccionado]

    # --- Lista de dependencias únicas desde usuarios activos ---
    dependencias_disponibles = sorted(set(u["dependencia"] for u in usuarios_data if u["activo"] and u["dependencia"]))

    # --- Seleccionar nueva dependencia ---
    nueva_dependencia = st.selectbox("Nueva dependencia", dependencias_disponibles, index=dependencias_disponibles.index(agente.get("dependencia", "")))

    # --- Filtrar evaluadores por esa dependencia ---
    evaluadores_opciones = [u for u in usuarios_data if u["dependencia"] == nueva_dependencia and u["activo"]]
    opciones_evaluador = {u["apellido_nombre"]: u["usuario"] for u in evaluadores_opciones}

    # --- Determinar evaluador actual por nombre ---
    usuario_actual = agente.get("evaluador_2024", "")
    nombre_actual = next((u["apellido_nombre"] for u in usuarios_data if u["usuario"] == usuario_actual), "[No asignado]")

    # --- Selector de evaluador por nombre (guarda usuario internamente) ---
    nombre_evaluador = st.selectbox("Evaluador asignado (2024)", list(opciones_evaluador.keys()), index=0 if nombre_actual not in opciones_evaluador else list(opciones_evaluador.keys()).index(nombre_actual))

    # --- Botón para actualizar ---
    if st.button("Actualizar datos"):
        nuevo_usuario = opciones_evaluador[nombre_evaluador]
        # Buscar dependencia_general del evaluador
        dependencia_gral = mapa_usuarios[nuevo_usuario]["dependencia_general"]

        # Actualizar en Supabase
        supabase.table("agentes").update({
            "dependencia": nueva_dependencia,
            "dependencia_general": dependencia_gral,
            "evaluador_2024": nuevo_usuario
        }).eq("cuil", agente["cuil"]).execute()

        st.success("Datos actualizados correctamente.")

