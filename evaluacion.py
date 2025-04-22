import streamlit as st
from st_supabase_connection import SupabaseConnection

# Método 1: Conexión recomendada (usando API Supabase)
def conexion_oficial():
    st.title("📊 Conexión Oficial con Supabase")
    
    conn = st.connection("supabase", type=SupabaseConnection)
    
    # Consulta simple
    try:
        datos = conn.query("*", table="agentes", ttl="10m").execute()
        if datos.data:
            df = pd.DataFrame(datos.data)
            st.success(f"✅ {len(df)} registros cargados")
            st.dataframe(df)
        else:
            st.warning("No se encontraron datos en la tabla 'agentes'")
    except Exception as e:
        st.error(f"Error en consulta: {str(e)}")

# Método 2: Conexión directa PostgreSQL (alternativa)
def conexion_postgres():
    st.title("🐘 Conexión Directa PostgreSQL")
    
    from sqlalchemy import create_engine
    
    try:
        engine = create_engine(
            f"postgresql+psycopg2://{st.secrets.supabase_db.user}:"
            f"{st.secrets.supabase_db.password}@"
            f"{st.secrets.supabase_db.host}:"
            f"{st.secrets.supabase_db.port}/"
            f"{st.secrets.supabase_db.database}",
            connect_args={"sslmode": "require"}
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
