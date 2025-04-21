import streamlit as st
import json
import time
import yaml
import pandas as pd
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from sqlalchemy import create_engine

# ---- CONFIGURACIÓN DE PÁGINA ----
st.set_page_config(page_title="Evaluación de Desempeño", layout="wide")

# ---- CARGAR CONFIGURACIÓN DESDE YAML ----
with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

# ---- AUTENTICACIÓN ----
authenticator = stauth.Authenticate(
    credentials=config['credentials'],
    cookie_name=config['cookie']['name'],
    cookie_key=config['cookie']['key'],
    cookie_expiry_days=config['cookie']['expiry_days']
)

authenticator.login()

if st.session_state["authentication_status"]:
    authenticator.logout("Cerrar sesión", "sidebar")
    st.sidebar.success(f"Hola, {st.session_state['name']}")
    st.markdown("""<h1 style='font-size: 30px; color: white;'>📊 Evaluación de Desempeño</h1>""", unsafe_allow_html=True)
elif st.session_state["authentication_status"] is False:
    st.error("❌ Usuario o contraseña incorrectos.")
    st.stop()
elif st.session_state["authentication_status"] is None:
    st.warning("🔐 Ingresá tus credenciales para acceder al dashboard.")
    st.stop()

# ---- CONEXIÓN A SUPABASE (PostgreSQL) ----
engine = create_engine(st.secrets["supabase"]["uri"])

# ---- FORMULARIOS ----
with open("formularios.yaml", "r", encoding="utf-8") as f:
    config_formularios = yaml.safe_load(f)
    formularios = config_formularios["formularios"]
    clasificaciones = config_formularios["clasificaciones"]

opcion = st.sidebar.radio("📂 Navegación", ["📝 Instructivo", "📄 Formulario"])

if opcion == "📝 Instructivo":
    st.title("📝 Instructivo")
    st.markdown("""
    Bienvenido al sistema de Evaluación de Desempeño.  
    1. Seleccioná el formulario correspondiente.  
    2. Completá todos los factores.  
    3. Previsualizá y confirmá la evaluación.  
    """)

elif opcion == "📄 Formulario":
    tipo = st.selectbox(
        "Seleccione el tipo de formulario",
        options=[""] + list(formularios.keys()),
        format_func=lambda x: f"Formulario {x}" if x else "Seleccione una opción",
        key="select_tipo"
    )

    if tipo:
        agentes = pd.read_sql("SELECT cuil, apellido_nombre FROM agentes", engine)
        if agentes.empty:
            st.warning("⚠️ No hay agentes disponibles para evaluar.")
            st.stop()

        with st.form("form_eval"):
            seleccionado = st.selectbox("Nombre del evaluado", agentes["apellido_nombre"])
            agente = agentes[agentes["apellido_nombre"] == seleccionado].iloc[0]
            cuil = agente["cuil"]
            apellido_nombre = agente["apellido_nombre"]

            st.info(f"Seleccionaste: {apellido_nombre} (CUIL: {cuil})")
            st.form_submit_button("🔍 Previsualizar (solo test de conexión)")
