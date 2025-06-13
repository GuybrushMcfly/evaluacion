import streamlit as st
from supabase import create_client
import streamlit_authenticator as stauth
import json
import datetime

# ---- CONFIGURACIÓN ----
TIEMPO_MAX_SESION_MIN = 2  # Logout automático tras 2 minutos de inactividad

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)

def cargar_usuarios_y_autenticar():
    supabase = init_connection()

    # Forzar logout por inactividad
    ahora = datetime.datetime.now()
    if "last_activity" in st.session_state:
        tiempo_inactivo = (ahora - st.session_state["last_activity"]).total_seconds()
        if tiempo_inactivo > TIEMPO_MAX_SESION_MIN * 60:
            st.session_state.clear()
            st.warning("🔐 Sesión cerrada por inactividad.")
            if st.button("🔁 Volver al login"):
                st.rerun()
            st.stop()
    st.session_state["last_activity"] = ahora  # Actualizar tiempo de última acción

    # Cargar usuarios activos
    usuarios_result = supabase.table("usuarios")\
        .select("usuario, password, apellido_nombre, rol, activo")\
        .eq("activo", True)\
        .execute()

    credentials = {
        "usernames": {},
        "cookie": {
            "expiry_days": 0.0014,  # ~2 minutos
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
            .select("dependencia, dependencia_general, apellido_nombre, rol")\
            .eq("usuario", username).maybe_single().execute().data

        if usuario_data:
            # Limpiar sesión previa
            for key in ["usuario", "nombre_completo", "rol", "dependencia", "dependencia_general"]:
                st.session_state.pop(key, None)

            # Cargar nuevos datos de sesión
            st.session_state["usuario"] = username
            st.session_state["nombre_completo"] = usuario_data.get("apellido_nombre", "")
            st.session_state["dependencia"] = usuario_data.get("dependencia", "")

            # Parsear el rol (de string JSON a dict)
            rol_raw = usuario_data.get("rol", "")
            try:
                st.session_state["rol"] = json.loads(rol_raw) if isinstance(rol_raw, str) else rol_raw
            except Exception:
                st.session_state["rol"] = {}

            # Solo ciertos roles acceden a dependencia_general
            if any(st.session_state["rol"].get(r) for r in ["rrhh", "coordinador", "evaluador_general"]):
                st.session_state["dependencia_general"] = usuario_data.get("dependencia_general") or ""
            else:
                st.session_state["dependencia_general"] = ""

    return name, authentication_status, username, authenticator, supabase
