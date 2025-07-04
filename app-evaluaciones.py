

import streamlit as st
import json
from modules import auth
from views import instructivo, formularios, evaluaciones, rrhh, capacitacion, configuracion
import bcrypt

st.set_page_config(page_title="Evaluación de Desempeño", layout="wide", initial_sidebar_state="expanded")

st.sidebar.image("logo-cap.png", use_container_width=True)

# ---- AUTENTICACIÓN ----
name, authentication_status, username, authenticator, supabase, cambiar_password = auth.cargar_usuarios_y_autenticar()

# ---- CAMBIO DE CONTRASEÑA FORZADO ----
if cambiar_password:
    st.warning("🔐 Debe cambiar su contraseña para continuar.")
    st.markdown("**⚠️ Requisitos de la nueva contraseña:**\n- Mínimo 6 caracteres\n- Debe contener al menos un número")

    nueva = st.text_input("Nueva contraseña", type="password", key="nueva_password")
    repetir = st.text_input("Repetir contraseña", type="password", key="repetir_password")

    if nueva and repetir:
        if nueva != repetir:
            st.error("❌ Las contraseñas no coinciden.")
        elif not auth.contraseña_valida(nueva):
            st.error("❌ La contraseña debe tener al menos 6 caracteres y contener al menos un número.")
        elif st.button("Guardar nueva contraseña"):
            hashed = bcrypt.hashpw(nueva.encode(), bcrypt.gensalt()).decode()
            supabase.table("usuarios").update({
                "password": hashed,
                "cambiar_password": False
            }).eq("usuario", username).execute()

            st.success("✅ Contraseña actualizada correctamente.")
            st.rerun()  # vuelve a autenticar ahora sin cambiar_password

    else:
        st.info("Ingrese su nueva contraseña dos veces, y pulse ENTER para confirmar.")

    st.stop()

elif authentication_status:
    # Usuario autenticado, cargar datos y mostrar interfaz
    try:
        usuario_data = supabase.table("usuarios")\
            .select("apellido_nombre, rol")\
            .eq("usuario", username)\
            .execute()\
            .data

        if usuario_data:
            rol_data = usuario_data[0].get("rol", {})
            if isinstance(rol_data, str):
                try:
                    rol_data = json.loads(rol_data)
                except json.JSONDecodeError:
                    rol_data = {}
            if not isinstance(rol_data, dict):
                rol_data = {}

            st.session_state.update({
                "usuario": username,
                "nombre_completo": usuario_data[0]['apellido_nombre'],
                "rol": rol_data
            })
        else:
            st.error("❌ No se pudieron cargar los datos del usuario.")
            st.stop()

    except Exception as e:
        st.error(f"❌ Error al cargar datos del usuario: {str(e)}")
        st.stop()

    if not st.session_state.get("usuario") or not st.session_state.get("rol"):
        st.warning("⚠️ La sesión ha expirado o es inválida. Por favor, vuelva a iniciar sesión.")
        authenticator.logout("Cerrar sesión", "sidebar")
        st.stop()

    # ---- INTERFAZ DE USUARIO ----
    # ---- INTERFAZ DE USUARIO ----
    st.sidebar.success(f"{st.session_state['nombre_completo']}")
    authenticator.logout("Cerrar sesión", "sidebar")

    # ---- NAVEGACIÓN (con opción predeterminada según rol) ----
    opciones_menu = [
        "📝 Instructivo",
        "📄 Formularios",
        "📋 Evaluaciones",
        "👥 RRHH",
        "📘 Capacitación",
        "⚙️ Configuración"
    ]

    rol = st.session_state.get("rol", {})

    if rol.get("evaluador") or rol.get("evaluador_general"):
        indice_default = opciones_menu.index("📄 Formularios")
    elif rol.get("coordinador"):
        indice_default = opciones_menu.index("📘 Capacitación")
    else:
        indice_default = opciones_menu.index("📝 Instructivo")

    opcion = st.sidebar.radio("📂 Navegación", opciones_menu, index=indice_default)

    if opcion == "📝 Instructivo":
        instructivo.mostrar(supabase)

    elif opcion == "📄 Formularios":
        if rol.get("evaluador") or rol.get("evaluador_general"):
            formularios_data, clasificaciones_data = formularios.cargar_formularios()
            formularios.mostrar(supabase, formularios_data, clasificaciones_data)
        else:
            st.warning("⚠️ Esta sección está habilitada para otro rol.")

    elif opcion == "📋 Evaluaciones":
        if rol.get("evaluador") or rol.get("evaluador_general"):
            evaluaciones.mostrar(supabase)
        else:
            st.warning("⚠️ Esta sección está habilitada para otro rol.")

    elif opcion == "👥 RRHH":
        if rol.get("rrhh"):
            rrhh.mostrar(supabase)
        else:
            st.warning("⚠️ Esta sección está habilitada para otro rol.")

    elif opcion == "📘 Capacitación":
        if rol.get("coordinador"):
            capacitacion.mostrar(supabase)
        else:
            st.warning("⚠️ Esta sección está habilitada para otro rol.")

    elif opcion == "⚙️ Configuración":
        if rol.get("coordinador"):
            configuracion.mostrar(supabase)
        else:
            st.warning("⚠️ Esta sección está habilitada para otro rol.")


