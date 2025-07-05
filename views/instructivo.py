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
    
    # --- Filtros superiores ---
    col1, col2, col3 = st.columns([2, 2, 1])  # Corregí el número de columnas (antes tenía [2, 2, 1] para 3 columnas)
    
    with col1:
        nivel_filter = st.selectbox(
            "🎯 Filtrar por Nivel:",
            ["Todos"] + list(set([item.get('nivel', 'Sin nivel') for item in supabase.table("agentes").select("nivel").execute().data if item.get('nivel')])),
            key="nivel_filter_aggrid"
        )
    
    with col2:
        dependencia_filter = st.selectbox(
            "🏢 Filtrar por Dependencia:",
            ["Todas"] + list(set([item.get('dependencia', 'Sin dependencia') for item in supabase.table("agentes").select("dependencia").execute().data if item.get('dependencia')])),
            key="dependencia_filter_aggrid"
        )
    
    # --- Obtener registros con filtros aplicados ---
    query = supabase.table("agentes").select("apellido_nombre, dependencia, nivel")
    
    # Aplicar filtros
    if nivel_filter != "Todos":
        query = query.eq("nivel", nivel_filter)
    if dependencia_filter != "Todas":
        query = query.eq("dependencia", dependencia_filter)
    
    data = query.execute().data
    df = pd.DataFrame(data)
    
    if not df.empty:
        # Configuración CSS para multilínea y estilo
        custom_css = {
            ".ag-theme-streamlit": {
                "--ag-font-size": "14px",
                "--ag-cell-horizontal-padding": "15px",
                "--ag-cell-vertical-padding": "8px",
            },
            ".ag-cell": {
                "line-height": "1.5",
                "white-space": "normal !important",
                "display": "flex",
                "align-items": "center",
            },
            ".ag-header-cell-label": {
                "justify-content": "left",
            }
        }
    
        # Configurar AgGrid con multilínea
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_side_bar()
        gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren="Group checkbox select children")
        
        # Configuración para multilínea
        gb.configure_default_column(
            autoHeight=True,
            wrapText=True,
            cellStyle={"white-space": "normal", "line-height": "1.5"},
            suppressMenu=True,
            filterable=True
        )
        
        # Configurar columnas específicas con flex para mejor responsive
        gb.configure_column("apellido_nombre", 
                           header_name="Apellido y Nombre",
                           flex=2,
                           minWidth=200,
                           tooltipField="apellido_nombre")
        
        gb.configure_column("dependencia", 
                           header_name="Dependencia",
                           flex=2,
                           minWidth=200,
                           tooltipField="dependencia")
        
        gb.configure_column("nivel", 
                           header_name="Nivel",
                           width=150,
                           tooltipField="nivel")
    
        gridOptions = gb.build()
    
        # Mostrar la tabla con configuración mejorada
        grid_response = AgGrid(
            df,
            gridOptions=gridOptions,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=False,
            enable_enterprise_modules=True,
            height=500,  # Aumenté la altura para mejor visualización
            width='100%',
            reload_data=False,  # Cambiado a False para mejor performance
            custom_css=custom_css,
            theme='streamlit',
            key="agentes_grid"
        )
        
        # Obtener datos modificados
        updated_df = grid_response['data']
        selected_rows = grid_response['selected_rows']
        
        # Mostrar botón de descarga para AgGrid
        if not df.empty:
            # Crear Excel en memoria
            from io import BytesIO
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Agentes')
            
            st.download_button(
                label="📥 Descargar Excel (AgGrid)",
                data=buffer.getvalue(),
                file_name=f"agentes_aggrid_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_aggrid"
            )
        
        # Mostrar información adicional si hay filas seleccionadas
        if selected_rows is not None and len(selected_rows) > 0:
            st.subheader("Filas seleccionadas:")
            st.dataframe(selected_rows)
            
    else:
        st.warning("No hay datos disponibles en la tabla agentes")
    
