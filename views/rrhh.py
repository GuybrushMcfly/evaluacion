import streamlit as st

def mostrar(supabase):
    st.header("📁 Sección RRHH")
    
    st.info("Esta sección está reservada para el personal de RRHH o coordinadores.")
    
    # Ejemplo: contar evaluaciones registradas
    evaluaciones = supabase.table("evaluaciones").select("id_evaluacion").execute().data
    total = len(evaluaciones)
    st.metric("Evaluaciones registradas", total)

    # A futuro: más paneles, búsquedas, cruces, exportaciones, etc.
