import streamlit as st
import json
from modules import auth
from views import instructivo, formularios, evaluaciones, rrhh, capacitacion, configuracion

# ---- CONFIGURACIÓN DE PÁGINA ----
st.set_page_config(page_title="Evaluación de Desempeño", layout="wide")

# ---- SIDEBAR: LOGO SIEMPRE ----
st.sidebar.image("logo-cap.png", use_container_width=True)

# ---- AUTENTICACIÓN ----
name, authentication_status, username, authenticator, supabase = auth.cargar_usuarios_y_autenticar()

# ---- SIDEBAR PRE-LOGIN ----
if authentication_status is None:
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Bienvenido/a")
    # Widget dummy para mantener la barra visible, pero minimalista
    st.sidebar.selectbox(" ", [" "], index=0, disabled=True)

# ---- MANEJO DE SESIÓN ----
if authentication_status:
    # Cargar datos del usuario
    try:
        usuario_data = (
            supabase
            .table("usuarios")
            .select("apellido_nombre, rol")
            .eq("usuario", username)
            .execute()
            .data
        )
        if not usuario_data:
            st.error("❌ No se pudieron cargar los datos del usuario.")
            st.stop()

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
            "nombre_completo": usuario_data[0]["apellido_nombre"],
            "rol": rol_data
        })

    except Exception as e:
        st.error(f"❌ Error al cargar datos del usuario: {e}")
        st.stop()

    # Validar sesión
    if not st.session_state.get("usuario") or not st.session_state.get("rol"):
        st.warning("⚠️ La sesión ha expirado o es inválida. Vuelva a iniciar sesión.")
        authenticator.logout("Cerrar sesión", "sidebar")
        st.stop()

    # ---- INTERFAZ POST-LOGIN ----
    st.sidebar.success(f"{st.session_state['nombre_completo']}")
    authenticator.logout("Cerrar sesión", "sidebar")

    # Navegación
    opcion = st.sidebar.radio(
        "📂 Navegación",
        [
            "📝 Instructivo",
            "📄 Formularios",
            "📋 Evaluaciones",
            "👥 RRHH",
            "📘 Capacitación",
            "⚙️ Configuración"
        ]
    )

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
    st.sidebar.error("❌ Usuario o contraseña incorrectos.")
    authenticator.logout("Cerrar sesión", "sidebar")
