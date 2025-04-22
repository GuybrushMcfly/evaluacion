import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Prueba de consulta
@st.cache_data(ttl=600)
def get_agentes():
    return supabase.table("agentes").select("apellido_nombre, cuil").execute()

st.title("👥 Agentes disponibles")

try:
    result = get_agentes()
    agentes = result.data
    nombres = [a["apellido_nombre"] for a in agentes]
    seleccionado = st.selectbox("Seleccione un agente", nombres)
    st.success(f"Seleccionaste a: {seleccionado}")
except Exception as e:
    st.error(f"Error: {e}")
