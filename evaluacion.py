import streamlit as st
from supabase import create_client, Client
import pandas as pd

# ───── CONEXIÓN ─────
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        client = create_client(url, key)
        st.success("✅ Conexión con Supabase establecida")
        return client
    except Exception as e:
        st.error(f"❌ Error al conectar con Supabase: {e}")
        st.stop()

supabase = init_connection()

# ───── DEBUGGING ─────
st.subheader("Información de depuración")
# Listar tablas disponibles
try:
    tables = supabase.table("pg_catalog.pg_tables").select("tablename").eq("schemaname", "public").execute()
    st.write("Tablas disponibles:", [table["tablename"] for table in tables.data])
except Exception as e:
    st.write("No se pudieron listar las tablas:", e)

# ───── CONSULTA ─────
@st.cache_data(ttl=600)
def obtener_agentes():
    result = supabase.table("agentes").select("*").limit(10).execute()
    # Mostrar resultado completo para depuración
    st.write("Resultado completo:", result)
    return result.data if result.data else []

# ───── UI ─────
st.title("👥 Primeros 10 registros de la tabla 'agentes'")
try:
    agentes = obtener_agentes()
    if agentes:
        df = pd.DataFrame(agentes)
        st.dataframe(df)
    else:
        st.warning("⚠️ La tabla 'agentes' está vacía o no se pudo leer correctamente.")
        
        # Intenta una consulta alternativa para verificar
        st.subheader("Probando consulta alternativa")
        try:
            count = supabase.table("agentes").select("count", count="exact").execute()
            st.write(f"Número de registros en la tabla: {count.count}")
        except Exception as e:
            st.error(f"Error en consulta alternativa: {e}")
            
except Exception as e:
    st.error(f"❌ Error al consultar Supabase:\n\n{e}")
