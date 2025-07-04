import streamlit as st

def mostrar(supabase):
    st.title("📝 Instructivo")
    st.markdown("""
    Bienvenido al sistema de Evaluación de Desempeño.  
    1. Seleccione el formulario correspondiente.  
    2. Complete todos los factores.  
    3. Previsualice y confirme la evaluación.  
    """)


    st.markdown("---")
    st.subheader("🗃️ Registros en tabla `casp`")

    # --- Obtener registros ---
    data = supabase.table("casp").select("*").execute().data

    if not data:
        st.info("No hay registros cargados aún.")
        return

    # --- Crear selección para cada fila ---
    seleccionados = []
    for fila in data:
        col1, col2 = st.columns([6, 1])
        with col1:
            st.write(f"🔹 {fila['nombre']}")
        with col2:
            marcado = st.checkbox("", key=f"check_{fila['id']}")
            if marcado:
                seleccionados.append(fila['id'])

    # --- Botón para borrar seleccionados ---
    if seleccionados:
        if st.button("🗑️ Borrar seleccionados"):
            for id_ in seleccionados:
                supabase.table("casp").delete().eq("id", id_).execute()
            st.success(f"{len(seleccionados)} registro(s) borrado(s).")
            st.experimental_rerun()
