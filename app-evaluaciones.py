import streamlit as st
from views import instructivo
from modules import auth
import json

# ---- CONFIGURACIÓN DE PÁGINA ----
st.set_page_config(page_title="Evaluación de Desempeño", layout="wide")

# ---- AUTENTICACIÓN ----
name, authentication_status, username, authenticator, supabase = auth.cargar_usuarios_y_autenticar()

# ---- MANEJO DE SESIÓN ----
if authentication_status:
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
        st.warning("⚠️ La sesión ha expirado o es inválida. Por favor, volvé a iniciar sesión.")
        authenticator.logout("Cerrar sesión", "sidebar")
        st.stop()

    # ---- INTERFAZ ----
    st.sidebar.success(f"Hola, {st.session_state['nombre_completo']}")
    authenticator.logout("Cerrar sesión", "sidebar")

    opcion = st.sidebar.radio("📂 Navegación", [
        "📝 Instructivo"
    ])

    if opcion == "📝 Instructivo":
        instructivo.mostrar()

elif authentication_status is False:
    st.error("❌ Usuario o contraseña incorrectos.")
elif authentication_status is None:
    st.warning("🔐 Ingresá tus credenciales para acceder al sistema.")
