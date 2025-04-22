import streamlit as st
import psycopg2

st.title("📋 Tablas disponibles en Supabase")

try:
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
        st.success("✅ Conectado a Supabase")
        st.write("📄 Tablas en el esquema público:")
        st.write(tablas)

except Exception as e:
    st.error(f"❌ Error al conectar o consultar Supabase:\n\n{e}")
