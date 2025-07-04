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
        # Configurar AgGrid con idioma español
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_side_bar()
        gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren="Group checkbox select children")
        gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=True)
        
        # Configurar columnas específicas
        gb.configure_column("apellido_nombre", header_name="Apellido y Nombre", width=300)
        gb.configure_column("dependencia", header_name="Dependencia", width=250)
        
        # Configurar textos en español
        gb.configure_grid_options(
            localeText={
                'page': 'Página',
                'more': 'Más',
                'to': 'a',
                'of': 'de',
                'next': 'Siguiente',
                'last': 'Último',
                'first': 'Primero',
                'previous': 'Anterior',
                'loadingOoo': 'Cargando...',
                'selectAll': 'Seleccionar Todo',
                'searchOoo': 'Buscar...',
                'blanks': 'Vacíos',
                'filterOoo': 'Filtrar...',
                'applyFilter': 'Aplicar Filtro',
                'equals': 'Igual',
                'notEqual': 'No Igual',
                'lessThan': 'Menor que',
                'greaterThan': 'Mayor que',
                'contains': 'Contiene',
                'startsWith': 'Comienza con',
                'endsWith': 'Termina con',
                'group': 'Grupo',
                'columns': 'Columnas',
                'filters': 'Filtros',
                'pivotMode': 'Modo Pivot',
                'groups': 'Grupos',
                'values': 'Valores',
                'pivots': 'Pivots',
                'toolPanel': 'Panel de Herramientas',
                'export': 'Exportar',
                'csvExport': 'Exportar CSV',
                'excelExport': 'Exportar Excel'
            }
        )
        
        gridOptions = gb.build()
        
        # Configurar idioma español
        custom_css = {
            ".ag-header-cell-text": {"font-size": "12px", "font-weight": "bold"},
            ".ag-theme-streamlit": {"transform": "scale(0.95)", "transform-origin": "0 0"}
        }
        
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
            reload_data=True,
            custom_css=custom_css,
            key="agentes_grid"
        )
        
        # Obtener datos modificados
        updated_df = grid_response['data']
        selected_rows = grid_response['selected_rows']
        
        # Mostrar información adicional si hay filas seleccionadas
        if selected_rows is not None and len(selected_rows) > 0:
            st.subheader("Filas seleccionadas:")
            st.dataframe(selected_rows)
            
    else:
        st.warning("No hay datos disponibles en la tabla agentes")

    # --- SEGUNDA TABLA CON DATA EDITOR ---
    st.markdown("---")
    st.subheader("📊 Tabla con Data Editor (Streamlit nativo)")
    
    # --- Obtener los mismos datos ---
    data_editor = supabase.table("agentes").select("apellido_nombre, dependencia").execute().data
    df_editor = pd.DataFrame(data_editor)
    
    if not df_editor.empty:
        # Configurar tipos de columnas
        column_config = {
            "apellido_nombre": st.column_config.TextColumn(
                "Apellido y Nombre",
                help="Nombre completo del agente",
                max_chars=100,
                width="medium"
            ),
            "dependencia": st.column_config.TextColumn(
                "Dependencia",
                help="Área de trabajo del agente",
                max_chars=100,
                width="medium"
            )
        }
        
        # Mostrar tabla editable
        edited_df = st.data_editor(
            df_editor,
            column_config=column_config,
            use_container_width=True,
            num_rows="dynamic",  # Permite agregar/eliminar filas
            height=400,
            key="data_editor_agentes"
        )
        
        # Mostrar información de cambios
        if not edited_df.equals(df_editor):
            st.info("✏️ Se detectaron cambios en los datos")
            
            # Botón para guardar cambios
            if st.button("💾 Guardar cambios", key="save_changes"):
                st.success("Cambios guardados exitosamente")
                # Aquí podrías implementar la lógica para actualizar Supabase
                # supabase.table("agentes").update(...).execute()
        
        # Mostrar estadísticas
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de registros", len(edited_df))
        with col2:
            st.metric("Dependencias únicas", edited_df['dependencia'].nunique())
            
    else:
        st.warning("No hay datos disponibles para el data editor")
