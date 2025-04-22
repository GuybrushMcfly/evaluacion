import streamlit as st
from supabase import create_client, Client
import pandas as pd

# ───── CONEXIÓN ─────
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    #key = st.secrets["SUPABASE_KEY"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    
    return create_client(url, key)

supabase = init_connection()

# ───── CONSULTA ─────
@st.cache_data(ttl=600)
def obtener_agentes():
    result = supabase.table("agentes").select("*").limit(10).execute()
    return result.data if result.data else []

# ───── UI ─────
st.title("👥 Primeros 10 registros de la tabla 'agentes'")

try:
    agentes = obtener_agentes()
    if agentes:
        df = pd.DataFrame(agentes)
        st.dataframe(df)
    else:
        st.warning("No se encontraron registros en la tabla.")
except Exception as e:
    st.error(f"❌ Error al consultar Supabase:\n\n{e}")
