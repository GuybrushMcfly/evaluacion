import streamlit as st
import pandas as pd

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

    # --- Obtener registros y convertirlos a DataFrame ---
    data = supabase.table("casp").select("*").execute().data
    
    if not data:
        st.info("No hay registros cargados aún.")
        return
    
    df = pd.DataFrame(data)
    
    # --- Mostrar tabla con checkboxes ---
    st.markdown("**Seleccione registros para borrar:**")
    
    # Crear columna de selección
    df['Seleccionar'] = False
    
    # Mostrar tabla editable con checkboxes
    edited_df = st.data_editor(
        df,
        column_config={
            "Seleccionar": st.column_config.CheckboxColumn(
                "Seleccionar",
                help="Seleccione registros para borrar",
                default=False,
            ),
            "id": None  # Ocultar columna ID si lo prefieres
        },
        hide_index=True,
        use_container_width=True,
        key="data_editor"
    )
    
    # Obtener IDs de los registros seleccionados
    seleccionados = edited_df[edited_df['Seleccionar']]['id'].tolist()
    
    # --- Botón para borrar seleccionados ---
    if seleccionados:
        if st.button("🗑️ Borrar seleccionados", type="primary"):
            for id_ in seleccionados:
                supabase.table("casp").delete().eq("id", id_).execute()
            st.success(f"{len(seleccionados)} registro(s) borrado(s).")
            st.rerun()  # Recargar la página para ver los cambios
