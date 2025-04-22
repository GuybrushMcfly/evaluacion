import streamlit as st
from supabase import create_client, Client
import pandas as pd

# ───── CONEXIÓN ─────
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        # Asegúrate de estar usando la service_role key, no la anon key
        key = st.secrets["SUPABASE_KEY"]  # O como sea que la hayas llamado
        client = create_client(url, key)
        st.success("✅ Conexión con Supabase establecida")
        return client
    except Exception as e:
        st.error(f"❌ Error al conectar con Supabase: {e}")
        st.stop()

supabase = init_connection()

# ───── CONSULTA ─────
@st.cache_data(ttl=600)
def obtener_agentes():
    try:
        # Opción 1: Usar el cliente normal
        result = supabase.table("agentes").select("*").limit(10).execute()
        # Mostrar resultado para depuración
        st.write("Respuesta de la API:", result)
        return result.data
    except Exception as e:
        st.error(f"Error en la consulta: {e}")
        return []

# ───── UI ─────
st.title("👥 Primeros 10 registros de la tabla 'agentes'")

# Botón para limpiar caché si necesitas probar diferentes configuraciones
if st.button("Limpiar caché"):
    st.cache_data.clear()
    st.rerun()

try:
    agentes = obtener_agentes()
    if agentes:
        df = pd.DataFrame(agentes)
        st.dataframe(df)
    else:
        st.warning("⚠️ La tabla 'agentes' no devolvió registros.")
        
        # Añadir información sobre RLS
        st.info("""
        Parece que hay un problema de permisos. Verifica:
        1. Si estás usando la service_role key de Supabase (tiene acceso completo)
        2. Si hay políticas RLS activas en tu tabla 'agentes'
        
        Para ver/modificar las políticas RLS:
        - Ve a Supabase Dashboard → Authentication → Policies
        - Busca la tabla 'agentes' y revisa sus políticas
        """)
        
        # Opción para deshabilitar temporalmente RLS para pruebas
        st.code("""
        -- Ejecuta esto en el SQL Editor de Supabase para deshabilitar RLS temporalmente
        -- (Solo para pruebas, no recomendado en producción)
        ALTER TABLE agentes DISABLE ROW LEVEL SECURITY;
        
        -- Para volver a habilitar RLS después:
        -- ALTER TABLE agentes ENABLE ROW LEVEL SECURITY;
        """)
except Exception as e:
    st.error(f"❌ Error al consultar Supabase:\n\n{e}")
