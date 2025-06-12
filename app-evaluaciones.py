import streamlit as st
from views import instructivo  # importar la vista que ya creamos

# ---- CONFIGURACIÓN DE PÁGINA ----
st.set_page_config(page_title="Evaluación de Desempeño", layout="wide")

# ---- NAVEGACIÓN ----
opcion = st.sidebar.radio("📂 Navegación", [
    "📝 Instructivo"
])

# ---- RENDERIZAR SECCIÓN ----
if opcion == "📝 Instructivo":
    instructivo.mostrar()
