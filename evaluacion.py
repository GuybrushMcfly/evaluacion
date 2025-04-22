import streamlit as st
from supabase import create_client, Client

# ───── CONEXIÓN ─────
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ───── CONSULTA ─────
@st.cache_data(ttl=600)
def get_agentes():
    response = supabase.table("agentes").select("cuil, apellido_nombre").order("apellido_nombre").execute()
    return response.data  # Convertido a lista de dicts

# ───── UI ─────
st.title("👥 Agentes disponibles")

try:
    agentes = get_agentes()
    if not agentes:
        st.warning("No hay agentes disponibles.")
    else:
        nombres = [a["apellido_nombre"] for a in agentes]
        seleccionado = st.selectbox("Seleccioná una persona", nombres)
        st.success(f"Seleccionaste a: {seleccionado}")
except Exception as e:
    st.error(f"❌ Error al cargar datos: {e}")
