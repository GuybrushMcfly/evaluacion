import streamlit as st
from supabase import create_client
import pandas as pd

# ─── Conexión ───
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

st.title("📋 Tablas disponibles en Supabase")

try:
    # Ejecutar SQL crudo para listar tablas
    result = supabase.rpc(
        "execute_sql",  # Asegurate de tener la función RPC en Supabase si vas por esta vía
        {"query": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"}
    ).execute()

    # O bien, directamente con psycopg2 si estás usando SQLAlchemy

    import psycopg2
    conn = psycopg2.connect(
        host=st.secrets["supabase_db"]["host"],
        port=st.secrets["supabase_db"]["port"],
        dbname=st.secrets["supabase_db"]["database"],
        user=st.secrets["supabase_db"]["user"],
        password=st.secrets["supabase_db"]["password"],
        sslmode="require"
    )

    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tablas = [r[0] for r in cur.fetchall()]
        st.success("✅ Conectado y consulta exitosa.")
        st.write("📄 Tablas encontradas:")
        st.write(tablas)

except Exception as e:
    st.error(f"❌ Error al consultar las tablas: {e}")
