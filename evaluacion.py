import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from sqlalchemy import create_engine
import socket
from urllib.parse import quote_plus

# Solución para el error IPv6
def resolve_ipv4(hostname):
    try:
        return socket.gethostbyname(hostname)
    except:
        return hostname

# Método 1: Conexión oficial con resolución IPv4
def conexion_oficial():
    st.title("📊 Conexión Oficial con Supabase (IPv4)")
    
    try:
        # Forzar resolución IPv4
        resolved_host = resolve_ipv4(st.secrets.supabase_db.host)
        
        conn = st.connection("supabase", type=SupabaseConnection, 
                           host=resolved_host,
                           options={"sslmode": "require"})
        
        datos = conn.query("*", table="agentes", ttl="10m").execute()
        
        if datos.data:
            df = pd.DataFrame(datos.data)
            st.success(f"✅ {len(df)} registros cargados")
            st.dataframe(df)
        else:
            st.warning("No se encontraron datos en la tabla 'agentes'")
    except Exception as e:
        st.error(f"Error en consulta: {str(e)}")

# Método 2: Conexión PostgreSQL con parámetros optimizados
def conexion_postgres():
    st.title("🐘 Conexión PostgreSQL Optimizada")
    
    try:
        # Forzar IPv4 y codificar contraseña
        resolved_host = resolve_ipv4(st.secrets.supabase_db.host)
        encoded_password = quote_plus(st.secrets.supabase_db.password)
        
        engine = create_engine(
            f"postgresql+psycopg2://{st.secrets.supabase_db.user}:"
            f"{encoded_password}@{resolved_host}:"
            f"{st.secrets.supabase_db.port}/"
            f"{st.secrets.supabase_db.database}",
            connect_args={
                "sslmode": "require",
                "connect_timeout": 5,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10
            },
            pool_pre_ping=True,
            pool_recycle=300
        )
        
        df = pd.read_sql("SELECT * FROM agentes LIMIT 1000", engine)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error PostgreSQL: {str(e)}")

# Selección del método
opcion = st.sidebar.selectbox(
    "Método de conexión",
    ["Oficial (API Supabase)", "Directa (PostgreSQL)"]
)

if opcion == "Oficial (API Supabase)":
    conexion_oficial()
else:
    conexion_postgres()
