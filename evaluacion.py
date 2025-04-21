import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# Conectar a Supabase usando credenciales en secrets.toml
supabase = st.secrets["supabase"]
engine = create_engine(
    f'postgresql+psycopg2://{supabase["user"]}:{supabase["password"]}@{supabase["host"]}:{supabase["port"]}/{supabase["database"]}',
    connect_args={"sslmode": "require"}
)

st.title("🔍 Lista de personas en la tabla 'agentes'")

try:
    df = pd.read_sql("SELECT cuil, apellido_nombre FROM agentes ORDER BY apellido_nombre", engine)
    st.success(f"Se cargaron {len(df)} agentes")
    st.dataframe(df)
except Exception as e:
    st.error(f"❌ Error al conectar o consultar Supabase:\n\n{str(e)}")
