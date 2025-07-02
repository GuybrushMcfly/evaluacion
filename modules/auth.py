import streamlit as st
from supabase import create_client
import streamlit_authenticator as stauth
import json
import datetime
import bcrypt

TIEMPO_MAX_SESION_MIN = 10

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)

def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def cargar_usuarios_y_autenticar():
    supabase = init_connection()

    # Logout automático por inactividad
    ahora = datetime.datetime.now()
    if "last_activity" in st.session_state:
        if (ahora - st.session_state["last_activity"]).total_seconds() > TIEMPO_MAX_SESION_MIN * 60:
            st.session_state.clear()
            st.warning("🔐 Sesión cerrada por inactividad.")
            if st.button("🔁 Volver al login"):
                st.rerun()
            st.stop()
    st.session_state["last_activity"] = ahora

    # Cargar usuarios activos
    usuarios_result = supabase.table("usuarios")\
        .select("usuario, password, apellido_nombre, rol, activo")\
        .eq("activo", True).execute()

    credentials = {
        "usernames": {},
        "cookie": {
            "expiry_days": 0.0014,
            "key": "clave_segura_super_oculta",
            "name": "evaluacion_app"
        }
    }

    for u in usuarios_result.data:
        usuario = u.get("usuario", "").strip().lower()
        password = u.get("password", "")
        nombre = u.get("apellido_nombre", "")
        if not usuario or not password or not nombre:
            continue
        if not password.startswith("$2b$"):
            continue
        credentials["usernames"][usuario] = {
            "name": nombre,
            "password": password,
            "email": f"{usuario}@indec.gob.ar"
        }

    if not credentials["usernames"]:
        st.error("❌ No se encontraron usuarios válidos.")
        st.stop()

    # Autenticación
    authenticator = stauth.Authenticate(
        credentials=credentials,
        cookie_name=credentials["cookie"]["name"],
        cookie_key=credentials["cookie"]["key"],
        cookie_expiry_days=credentials["cookie"]["expiry_days"]
    )

    try:
        name, authentication_status, username = authenticator.login()
    except KeyError as e:
        st.error(f"❌ Usuario inválido: {e}")
        st.stop()

    if authentication_status:
        usuario_data = supabase.table("usuarios")\
            .select("dependencia, dependencia_general, apellido_nombre, rol, cambiar_password")\
            .eq("usuario", username).maybe_single().execute().data

        if not usuario_data:
            st.error("❌ No se pudieron cargar los datos del usuario.")
            st.stop()

        if usuario_data.get("cambiar_password", False):
            st.warning("🔐 Debe cambiar su contraseña para continuar.")
            nueva = st.text_input("Nueva contraseña", type="password")
            repetir = st.text_input("Repetir contraseña", type="password")
            if nueva and repetir:
                if nueva != repetir:
                    st.error("❌ Las contraseñas no coinciden.")
                elif len(nueva) < 6:
                    st.error("❌ La contraseña debe tener al menos 6 caracteres.")
                elif st.button("Guardar nueva contraseña"):
                    hashed = hashear_password(nueva)
                    supabase.table("usuarios").update({
                        "password": hashed,
                        "cambiar_password": False
                    }).eq("usuario", username).execute()
                    st.success("✅ Contraseña actualizada. Por favor, vuelva a iniciar sesión.")
                    authenticator.logout("🔁 Cerrar sesión", "main")
                    st.stop()
            else:
                st.info("Ingrese su nueva contraseña dos veces para confirmar.")
            return None, False, username, authenticator, supabase  # Previene continuar sin cambiar clave

        # Guardar datos de sesión como antes
        for key in ["usuario", "nombre_completo", "rol", "dependencia", "dependencia_general"]:
            st.session_state.pop(key, None)

        st.session_state["usuario"] = username
        st.session_state["nombre_completo"] = usuario_data.get("apellido_nombre", "")
        st.session_state["dependencia"] = usuario_data.get("dependencia", "")

        rol_raw = usuario_data.get("rol", "")
        try:
            st.session_state["rol"] = json.loads(rol_raw) if isinstance(rol_raw, str) else rol_raw
        except Exception:
            st.session_state["rol"] = {}

        if any(st.session_state["rol"].get(r) for r in ["rrhh", "coordinador", "evaluador_general"]):
            st.session_state["dependencia_general"] = usuario_data.get("dependencia_general") or ""
        else:
            st.session_state["dependencia_general"] = ""

    return name, authentication_status, username, authenticator, supabase
