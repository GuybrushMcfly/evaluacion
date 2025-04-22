from supabase import create_client, Client
import pandas as pd
import streamlit as st
import pandas as pd
import time
import yaml
from yaml.loader import SafeLoader
from sqlalchemy import create_engine
import streamlit_authenticator as stauth
import psycopg2

# ───── CONEXIÓN ─────
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    #key = st.secrets["SUPABASE_KEY"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    
    return create_client(url, key)

supabase = init_connection()

# ───── CONSULTA ─────
@st.cache_data(ttl=600)
def obtener_agentes():
    result = supabase.table("agentes").select("*").limit(10).execute()
    return result.data if result.data else []

supabase = init_connection()


## ---- CONFIGURACIÓN DE PÁGINA ----
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


# ---- CARGAR FORMULARIOS ----
with open("formularios.yaml", "r", encoding="utf-8") as f:
    config_formularios = yaml.safe_load(f)
    formularios = config_formularios["formularios"]
    clasificaciones = config_formularios["clasificaciones"]

# ---- NAVEGACIÓN ----
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
    # Obtener lista de agentes desde Supabase
    agentes_data = supabase.table("agentes").select("cuil, apellido_nombre").order("apellido_nombre").execute().data

    if not agentes_data:
        st.warning("⚠️ No hay agentes cargados en la base de datos.")
        st.stop()

    opciones_agentes = [a["apellido_nombre"] for a in agentes_data]
    seleccionado = st.selectbox("👤 Seleccione un agente para evaluar", opciones_agentes)

    agente = next((a for a in agentes_data if a["apellido_nombre"] == seleccionado), None)

    if not agente:
        st.error("❌ No se pudo encontrar el agente seleccionado.")
        st.stop()

    # Mostrar tabla con info del agente seleccionado
    st.markdown("#### 📄 Datos del agente seleccionado")
    st.table(pd.DataFrame([agente])[["cuil", "apellido_nombre"]])

    tipo = st.selectbox(
        "📄 Seleccione el tipo de formulario",
        options=[""] + list(formularios.keys()),
        format_func=lambda x: f"Formulario {x}" if x else "Seleccione una opción",
        key="select_tipo"
    )

    if tipo != "":
        if 'previsualizado' not in st.session_state:
            st.session_state.previsualizado = False
        if 'confirmado' not in st.session_state:
            st.session_state.confirmado = False

        cuil = agente["cuil"]
        apellido_nombre = agente["apellido_nombre"]

        with st.form("form_eval"):
            factor_puntaje = {}
            puntajes = []
            respuestas_completas = True

            for i, bloque in enumerate(formularios[tipo]):
                st.subheader(bloque['factor'])
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

            previsualizar = st.form_submit_button("🔍 Previsualizar calificación")

        if previsualizar:
            if respuestas_completas:
                st.session_state.previsualizado = True
                st.session_state.puntajes = puntajes
                st.session_state.respuestas_completas = True
            else:
                st.error("❌ Complete todas las respuestas para previsualizar la calificación")
                st.session_state.previsualizado = False

        if st.session_state.previsualizado and st.session_state.respuestas_completas:
            total = sum(st.session_state.puntajes)
            rango = clasificaciones.get(tipo, [])
            clasificacion = next(
                (nombre for nombre, maxv, minv in rango if minv <= total <= maxv),
                "Sin clasificación"
            )

            st.markdown("---")
            st.markdown(f"### 📊 Puntaje preliminar: {total}")
            st.markdown(f"### 📌 Calificación estimada: **{clasificacion}**")
            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Sí, enviar evaluación"):
                    st.session_state.confirmado = True
                    tipo_formulario = tipo

                    # Guardar evaluación en tabla evaluaciones
                    engine.execute("""
                        INSERT INTO evaluaciones (cuil, apellido_nombre, anio, formulario, puntaje_total, evaluacion, evaluado_2025, factor_puntaje, _timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, now())
                    """, (
                        cuil, apellido_nombre, 2025, tipo_formulario, total, clasificacion, json.dumps(factor_puntaje)
                    ))

                    # Marcar como evaluado
                    engine.execute("UPDATE agentes SET evaluado_2025 = TRUE WHERE cuil = %s", (cuil,))

                    st.success(f"📤 Evaluación de {apellido_nombre} enviada correctamente")
                    st.balloons()
                    time.sleep(2)

                    for key in list(st.session_state.keys()):
                        if key.startswith("factor_") or key in ["select_tipo", "previsualizado", "confirmado", "puntajes", "respuestas_completas", "last_tipo"]:
                            del st.session_state[key]

                    st.rerun()

            with col2:
                if st.button("❌ No, revisar opciones"):
                    st.session_state.previsualizado = False
                    st.warning("🔄 Por favor revise las opciones seleccionadas")

        if 'last_tipo' in st.session_state and st.session_state.last_tipo != tipo:
            st.session_state.previsualizado = False
            st.session_state.confirmado = False
        st.session_state.last_tipo = tipo


