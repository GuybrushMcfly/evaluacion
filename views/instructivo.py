import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from io import BytesIO

def mostrar(supabase):
    st.title("📝 Instructivo")
    st.markdown("""
    Bienvenido al sistema de Evaluación de Desempeño.  
    1. Seleccione el formulario correspondiente.  
    2. Complete todos los factores.  
    3. Previsualice y confirme la evaluación.  
    """)

    st.markdown("---")
    st.subheader("🗃️ Registros en tabla `agentes`")
    
    # --- Filtros superiores ---
    col1, col2, col3 = st.columns([2, 2, 1])
    
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
    
    if nivel_filter != "Todos":
        query = query.eq("nivel", nivel_filter)
    if dependencia_filter != "Todas":
        query = query.eq("dependencia", dependencia_filter)
    
    data = query.execute().data
    df = pd.DataFrame(data)
    
    if not df.empty:
        # Configuración CSS para multilínea
        custom_css = {
            ".ag-cell": {
                "white-space": "normal !important",
                "line-height": "1.5",
                "display": "flex",
                "align-items": "center"
            }
        }

        # Configurar AgGrid
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(
            autoHeight=True,
            wrapText=True,
            cellStyle={"white-space": "normal", "line-height": "1.5"}
        )
        
        gb.configure_columns(
            ["apellido_nombre", "dependencia", "nivel"],
            headerClass="header-style",
            cellStyle={"text-align": "left"}
        )
        
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_side_bar()
        gb.configure_selection('multiple', use_checkbox=True)
        
        # Mostrar tabla
        grid_response = AgGrid(
            df,
            gridOptions=gb.build(),
            height=500,
            width='100%',
            custom_css=custom_css,
            theme='streamlit',
            enable_enterprise_modules=True
        )

        # Exportar a Excel (con verificación de openpyxl)
        try:
            buffer = BytesIO()
            df.to_excel(buffer, index=False, engine='openpyxl')  # Especifica el motor
            
            st.download_button(
                "📥 Descargar Excel",
                data=buffer.getvalue(),
                file_name="agentes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except ImportError:
            st.warning("Para exportar a Excel, instala openpyxl: pip install openpyxl")
        
        # Mostrar selección
        if grid_response['selected_rows']:
            st.subheader("Filas seleccionadas")
            st.write(grid_response['selected_rows'])
            
    else:
        st.warning("No hay datos disponibles")
