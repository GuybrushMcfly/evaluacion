import streamlit as st
from supabase import create_client
import streamlit_authenticator as stauth
import json

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)

def cargar_usuarios_y_autenticar():
    supabase = init_connection()

    usuarios_result = supabase.table("usuarios")\
        .select("usuario, password, apellido_nombre, rol, activo")\
        .eq("activo", True)\
        .execute()

    credentials = {
        "usernames": {},
        "cookie": {
            "expiry_days": 0.0104,  # 15 minutos
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
            st.session_state.update({
                "usuario": username,
                "nombre_completo": usuario_data.get("apellido_nombre", ""),
                "rol": usuario_data.get("rol", {}),
                "dependencia": usuario_data.get("dependencia", ""),
                "dependencia_general": usuario_data.get("dependencia_general", "")
            })
    
    return name, authentication_status, username, authenticator, supabase

