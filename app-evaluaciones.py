import streamlit as st
import json
from modules import auth
from views import instructivo, formularios, evaluaciones, rrhh, capacitacion, configuracion
import bcrypt

st.set_page_config(
    page_title="Evaluación de Desempeño",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mostrar logo siempre, incluso antes de login
st.sidebar.image("logo-cap.png", use_container_width=True)

# ---- AUTENTICACIÓN ----
# Ahora cargamos también cambiar_password, que indica si debe cambiar clave
name, authentication_status, username, authenticator, supabase, cambiar_password = auth.cargar_usuarios_y_autenticar()

if cambiar_password:
    st.warning("🔐 Debe cambiar su contraseña para continuar.")
    st.markdown("⚠️ Requisitos de la nueva contraseña:\n- Mínimo 6 caracteres\n- Debe contener al menos un número")
    
    nueva = st.text_input("Nueva contraseña", type="password")
    repetir = st.text_input("Repetir contraseña", type="password")
    
    if nueva and repetir:
        if nueva != repetir:
            st.error("❌ Las contraseñas no coinciden.")
        elif len(nueva) < 6 or not any(c.isdigit() for c in nueva):
            st.error("❌ La contraseña debe tener al menos 6 caracteres y contener al menos un número.")
        elif st.button("Guardar nueva contraseña"):
            hashed = bcrypt.hashpw(nueva.encode(), bcrypt.gensalt()).decode()
            supabase.table("usuarios").update({
                "password": hashed,
                "cambiar_password": False
            }).eq("usuario", username).execute()
            st.success("✅ Contraseña actualizada correctamente. Vuelva a iniciar sesión.")
            authenticator.logout("🔁 Cerrar sesión", "main")
            st.stop()
    else:
        st.info("Ingrese su nueva contraseña dos veces para confirmar.")
    
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
    st.sidebar.success(f"{st.session_state['nombre_completo']}")
    authenticator.logout("Cerrar sesión", "sidebar")

    # ---- NAVEGACIÓN ----
    opcion = st.sidebar.radio("📂 Navegación", [
        "📝 Instructivo",
        "📄 Formularios",
        "📋 Evaluaciones",
        "👥 RRHH",
        "📘 Capacitación",
        "⚙️ Configuración"
    ])

    if opcion == "📝 Instructivo":
        instructivo.mostrar()

    elif opcion == "📄 Formularios":
        if st.session_state["rol"].get("evaluador") or st.session_state["rol"].get("evaluador_general"):
            formularios_data, clasificaciones_data = formularios.cargar_formularios()
            formularios.mostrar(supabase, formularios_data, clasificaciones_data)
        else:
            st.warning("⚠️ Esta sección está habilitada para otro rol.")

    elif opcion == "📋 Evaluaciones":
        if st.session_state["rol"].get("evaluador") or st.session_state["rol"].get("evaluador_general"):
            evaluaciones.mostrar(supabase)
        else:
            st.warning("⚠️ Esta sección está habilitada para otro rol.")

    elif opcion == "👥 RRHH":
        if st.session_state["rol"].get("rrhh"):
            rrhh.mostrar(supabase)
        else:
            st.warning("⚠️ Esta sección está habilitada para otro rol.")

    elif opcion == "📘 Capacitación":
        if st.session_state["rol"].get("coordinador"):
            capacitacion.mostrar(supabase)
        else:
            st.warning("⚠️ Esta sección está habilitada para otro rol.")

    elif opcion == "⚙️ Configuración":
        if st.session_state["rol"].get("coordinador"):
            configuracion.mostrar(supabase)
        else:
            st.warning("⚠️ Esta sección está habilitada para otro rol.")

elif authentication_status is False:
    if st.session_state.get("usuario") is None:
        st.error("❌ Usuario o contraseña incorrectos.")

elif authentication_status is None:
    st.warning("🔐 Ingrese las credenciales para acceder al sistema.")
