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

# ───── DIAGNÓSTICO AVANZADO ─────
st.subheader("Diagnóstico de Supabase")

# Probemos primero si la tabla existe con una consulta que debería funcionar
try:
    # Intenta contar registros - esto verificará si la tabla existe
    result = supabase.table("agentes").select("count", count="exact").execute()
    st.write(f"La tabla 'agentes' existe. Conteo de registros: {result.count}")
    
    # Mostrar estructura de la tabla
    st.write("Verificando columnas de la tabla:")
    try:
        # Intentar obtener un solo registro para ver su estructura
        sample = supabase.table("agentes").select("*").limit(1).execute()
        if sample.data:
            st.write("Columnas disponibles:", list(sample.data[0].keys()))
        else:
            st.warning("La tabla existe pero parece estar vacía")
    except Exception as e:
        st.error(f"Error al verificar estructura: {e}")
        
except Exception as e:
    if "relation" in str(e) and "does not exist" in str(e):
        st.error("❌ La tabla 'agentes' no existe")
        
        # Intentar listar tablas disponibles usando el SQL directo
        try:
            result = supabase.rpc("list_tables").execute()
            st.write("Tablas disponibles:", result.data)
        except:
            # Si falla, podemos intentar un enfoque más directo
            try:
                # Crear una función RPC primero en Supabase
                st.info("Para ver las tablas disponibles, debes crear una función RPC en Supabase con este código:")
                st.code("""
                create or replace function list_tables()
                returns table (table_name text)
                language sql
                as $$
                  select tablename as table_name 
                  from pg_catalog.pg_tables
                  where schemaname = 'public'
                $$;
                """)
            except:
                pass
    else:
        st.error(f"Error diferente: {e}")

# ───── CONSULTA ORIGINAL ─────
st.title("👥 Consulta de tabla 'agentes'")
try:
    # Desactiva el cache para pruebas
    result = supabase.table("agentes").select("*").limit(10).execute()
    
    st.write("Resultado completo de la consulta para depuración:", result)
    
    if result.data:
        df = pd.DataFrame(result.data)
        st.dataframe(df)
    else:
        st.warning("⚠️ No se encontraron registros en la tabla 'agentes'.")
        st.info("Posibles razones:")
        st.markdown("""
        1. La tabla está realmente vacía
        2. Tu clave API no tiene permisos para ver los registros
        3. Existe alguna política RLS (Row Level Security) que filtra todos los registros
        4. La tabla existe en un esquema diferente a 'public'
        """)
        
        # Sugerir verificación directa
        st.info("💡 Verifica directamente en el Dashboard de Supabase si hay datos en esta tabla")
        
except Exception as e:
    st.error(f"❌ Error al consultar Supabase:\n\n{e}")
