import streamlit as st
from supabase import create_client, Client
import pandas as pd

# ───── CONEXIÓN ─────
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ───── CONSULTA ─────
@st.cache_data(ttl=600)
def obtener_agentes():
    response = supabase.table("agentes").select("*").limit(10).execute()
    return response.data

# ───── UI ─────
st.title("👥 Primeros 10 registros de la tabla 'agentes'")

try:
    datos = obtener_agentes()
    if not datos:
        st.warning("No se encontraron registros en la tabla.")
    else:
        df = pd.DataFrame(datos)
        st.dataframe(df)
except Exception as e:
    st.error(f"❌ Error al consultar Supabase: {e}")
