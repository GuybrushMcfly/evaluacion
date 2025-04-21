import streamlit as st
import firebase_admin
import json
import time
import yaml
import streamlit_authenticator as stauth
import pandas as pd
from yaml.loader import SafeLoader
from firebase_admin import credentials, firestore
from google.api_core import retry
from google.api_core.exceptions import RetryError, GoogleAPIError

# Configuración de reintentos para Firestore
custom_retry = retry.Retry(
    initial=1.0,
    maximum=10.0,
    multiplier=2.0,
    deadline=30.0,
    predicate=retry.if_exception_type(Exception)
)

# ---- CONFIGURACIÓN INICIAL ----
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            cred_json = json.loads(st.secrets["GOOGLE_FIREBASE_CREDS"])
            cred = credentials.Certificate(cred_json)
            firebase_admin.initialize_app(cred)
            return True
        except Exception as e:
            st.error(f"Error al inicializar Firebase: {str(e)}")
            return False
    return True

if not initialize_firebase():
    st.stop()

# Función segura para obtener cliente Firestore
@st.cache_resource
def get_firestore_client():
    try:
        return firestore.client()
    except Exception as e:
        st.error(f"Error al conectar con Firestore: {str(e)}")
        st.stop()

db = get_firestore_client()

# ---- CONFIGURACIÓN DE PÁGINA ----
st.set_page_config(page_title="Evaluación de Desempeño", layout="wide")

# ---- CARGAR CONFIGURACIÓN ----
@st.cache_data
def load_config():
    with open("config.yaml") as file:
        return yaml.load(file, Loader=SafeLoader)

@st.cache_data
def load_form_config():
    with open("formularios.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        return config["formularios"], config["clasificaciones"]

config = load_config()
formularios, clasificaciones = load_form_config()

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
    st.warning("🔒 Ingresá tus credenciales para acceder al dashboard.")
    st.stop()

# ---- FUNCIONES DE DATOS ----
def get_unevaluated_agents():
    try:
        agents_ref = db.collection("agentes").where("evaluado_2025", "==", False).stream()
        agents = []
        for doc in agents_ref:
            agent_data = doc.to_dict()
            agent_data["id"] = doc.id
            agents.append(agent_data)
        return sorted(agents, key=lambda x: x["apellido_nombre"])
    except Exception as e:
        st.error(f"Error al cargar agentes: {str(e)}")
        return []

def save_evaluation(evaluation_data):
    try:
        doc_id = f"{evaluation_data['cuil']}-2025"
        db.collection("evaluaciones").document(doc_id).set(evaluation_data)
        db.collection("agentes").document(evaluation_data['cuil']).update({"evaluado_2025": True})
        return True
    except Exception as e:
        st.error(f"Error al guardar evaluación: {str(e)}")
        return False

def get_all_evaluations():
    try:
        evaluations_ref = db.collection("evaluaciones").stream()
        return [e.to_dict() for e in evaluations_ref]
    except Exception as e:
        st.error(f"Error al cargar evaluaciones: {str(e)}")
        return []

# ---- INTERFAZ PRINCIPAL ----
opcion = st.sidebar.radio("📂 Navegación", ["📝 Instructivo", "📄 Formulario", "📋 Evaluaciones"])

if opcion == "📝 Instructivo":
    st.title("📝 Instructivo")
    st.markdown("""
    Bienvenido al sistema de Evaluación de Desempeño.  
    1. Seleccioná el formulario correspondiente.  
    2. Completá todos los factores.  
    3. Previsualizá y confirmá la evaluación.  
    """)

elif opcion == "📄 Formulario":
    st.title("📄 Formulario de Evaluación")
    
    # Selección de tipo de formulario
    tipo = st.selectbox(
        "Seleccione el tipo de formulario",
        options=[""] + list(formularios.keys()),
        format_func=lambda x: f"Formulario {x}" if x else "Seleccione una opción",
        key="form_type"
    )
    
    if not tipo:
        st.stop()

    # Cargar agentes no evaluados
    agentes = get_unevaluated_agents()
    if not agentes:
        st.warning("⚠️ No hay agentes disponibles para evaluar en 2025.")
        st.stop()

    # Selección de agente
    with st.form("agent_selection"):
        agente_seleccionado = st.selectbox(
            "Seleccione el agente a evaluar",
            options=[a["apellido_nombre"] for a in agentes],
            key="agent_select"
        )
        submit_agent = st.form_submit_button("Seleccionar Agente")

    if not submit_agent:
        st.stop()

    agente = next((a for a in agentes if a["apellido_nombre"] == agente_seleccionado), None)
    if not agente:
        st.error("Agente no encontrado")
        st.stop()

    # Formulario de evaluación
    with st.form("evaluation_form"):
        st.subheader(f"Evaluación para: {agente['apellido_nombre']}")
        
        factor_puntaje = {}
        puntajes = []
        respuestas_completas = True

        for i, bloque in enumerate(formularios[tipo]):
            st.markdown(f"### {bloque['factor']}")
            st.write(bloque['descripcion'])

            opciones = [texto for texto, _ in bloque['opciones']]
            seleccion = st.radio(
                label="Seleccione una opción",
                options=opciones,
                key=f"factor_{i}",
                index=None
            )

            if seleccion is not None:
                puntaje = dict(bloque['opciones'])[seleccion]
                puntajes.append(puntaje)
                clave = bloque['factor'].split(' ')[0].strip()
                factor_puntaje[f"Factor {clave}"] = puntaje
            else:
                respuestas_completas = False

        submitted = st.form_submit_button("🔍 Previsualizar calificación")

    if submitted:
        if not respuestas_completas:
            st.error("❌ Complete todas las respuestas para previsualizar la calificación")
            st.stop()

        total = sum(puntajes)
        rango = clasificaciones.get(tipo, [])
        clasificacion = next(
            (nombre for nombre, maxv, minv in rango if minv <= total <= maxv),
            "Sin clasificación"
        )

        st.markdown("---")
        st.markdown(f"### 📊 Puntaje preliminar: {total}")
        st.markdown(f"### 📌 Calificación estimada: **{clasificacion}**")
        st.markdown("---")

        if st.button("✅ Confirmar y enviar evaluación"):
            evaluation_data = {
                "apellido_nombre": agente['apellido_nombre'],
                "cuil": agente['cuil'],
                "anio": 2025,
                "formulario": tipo,
                "puntaje_total": total,
                "evaluacion": clasificacion,
                "evaluado_2025": True,
                "factor_puntaje": factor_puntaje,
                "_timestamp": firestore.SERVER_TIMESTAMP,
            }

            if save_evaluation(evaluation_data):
                st.success(f"📤 Evaluación de {agente['apellido_nombre']} enviada correctamente")
                st.balloons()
                time.sleep(2)
                st.rerun()

elif opcion == "📋 Evaluaciones":
    st.title("📋 Evaluaciones Registradas")
    
    evaluaciones = get_all_evaluations()
    if not evaluaciones:
        st.info("No hay evaluaciones registradas.")
        st.stop()

    df = pd.DataFrame(evaluaciones)
    st.dataframe(df[["apellido_nombre", "anio", "formulario", "puntaje_total", "evaluacion"]])
    
    st.markdown("### 🔁 Reevaluar Agentes")
    selected = st.multiselect(
        "Seleccione agentes para reevaluar",
        options=[e["apellido_nombre"] for e in evaluaciones]
    )
    
    if selected and st.button("Marcar para reevaluación"):
        for eval in evaluaciones:
            if eval["apellido_nombre"] in selected:
                try:
                    db.collection("agentes").document(eval['cuil']).update({"evaluado_2025": False})
                except Exception as e:
                    st.error(f"Error al actualizar {eval['apellido_nombre']}: {str(e)}")
        
        st.success(f"{len(selected)} agentes marcados para reevaluación")
        time.sleep(1)
        st.rerun()
