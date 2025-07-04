import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode


def mostrar(supabase):
    st.title("📝 Instructivo")
    st.markdown("""
    Bienvenido al sistema de Evaluación de Desempeño.  
    1. Seleccione el formulario correspondiente.  
    2. Complete todos los factores.  
    3. Previsualice y confirme la evaluación.  
    """)

    
    st.markdown("---")
    st.markdown("---")
    st.subheader("🗃️ Registros en tabla `agentes`")
    
    # --- Obtener registros y convertirlos a DataFrame ---
    data = supabase.table("agentes").select("apellido_nombre, dependencia").execute().data
    df = pd.DataFrame(data)
    
    if not df.empty:
        # Configurar AgGrid
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_side_bar()
        gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren="Group checkbox select children")
        gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=True)
        
        # Configurar columnas específicas
        gb.configure_column("apellido_nombre", header_name="Apellido y Nombre", width=300)
        gb.configure_column("dependencia", header_name="Dependencia", width=250)
        
        gridOptions = gb.build()
        
        # Mostrar la tabla
        grid_response = AgGrid(
            df,
            gridOptions=gridOptions,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=False,
            enable_enterprise_modules=True,
            height=400,
            width='100%',
            reload_data=True
        )
        
        # Obtener datos modificados
        updated_df = grid_response['data']
        selected_rows = grid_response['selected_rows']
        
        # Mostrar información adicional si hay filas seleccionadas
        if len(selected_rows) > 0:
            st.subheader("Filas seleccionadas:")
            st.dataframe(selected_rows)
            
    else:
        st.warning("No hay datos disponibles en la tabla agentes")
