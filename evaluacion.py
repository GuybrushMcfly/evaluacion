import streamlit as st
import firebase_admin
import json
import time
import yaml
import streamlit_authenticator as stauth
import pandas as pd
import re
from yaml.loader import SafeLoader
from firebase_admin import credentials, firestore


@st.cache_data
def cargar_formularios():
    with open("formularios.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["formularios"], config["clasificaciones"]

@st.cache_data(ttl=60)
def get_evaluaciones():
    return [doc.to_dict() for doc in db.collection("evaluaciones").stream()]

@st.cache_data(ttl=60)
def get_agentes():
    return {doc.id: doc.to_dict() for doc in db.collection("agentes").stream()}

@st.cache_data(ttl=60)
def get_agentes_para_evaluar():
    agentes_ref = db.collection("agentes").where("evaluado_2025", "==", False).stream()
    return [{**doc.to_dict(), "id": doc.id} for doc in agentes_ref]




# Inicializar Firebase solo una vez
if not firebase_admin._apps:
    cred_json = json.loads(st.secrets["GOOGLE_FIREBASE_CREDS"])
    cred = credentials.Certificate(cred_json)
    firebase_admin.initialize_app(cred)

# Conectar con Firestore
db = firestore.client()

# ---- CONFIGURACIÓN DE PÁGINA ----
st.set_page_config(page_title="Evaluación de Desempeño", layout="wide")
#st.sidebar.image("logo-cap.png", use_container_width=True)


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
    #st.title("📊 Dashboard Tramos Escalafonarios")
    st.markdown("""<h1 style='font-size: 30px; color: white;'>📊 Evaluación de Desempeño</h1>""", unsafe_allow_html=True)
elif st.session_state["authentication_status"] is False:
    st.error("❌ Usuario o contraseña incorrectos.")
    st.stop()
elif st.session_state["authentication_status"] is None:
    st.warning("🔒 Ingresá tus credenciales para acceder al dashboard.")
    st.stop()

st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)



#with open("formularios.yaml", "r", encoding="utf-8") as f:
#    config_formularios = yaml.safe_load(f)
#    formularios = config_formularios["formularios"]
#    clasificaciones = config_formularios["clasificaciones"]

formularios, clasificaciones = cargar_formularios()


# Menú lateral de navegación
opcion = st.sidebar.radio("📂 Navegación", ["📄 Formulario", "📋 Evaluaciones", "📝 Instructivo", "EVALUACIÓN GENERAL", ])


# Crear tabs
#tabs = st.tabs(["📄 Formulario", "📋 Evaluados"])

if opcion == "📝 Instructivo":
    st.title("📝 Instructivo")
    st.markdown("""
    Bienvenido al sistema de Evaluación de Desempeño.  
    1. Seleccioná el formulario correspondiente.  
    2. Completá todos los factores.  
    3. Previsualizá y confirmá la evaluación.  
    """)

elif opcion == "📄 Formulario":
    # Evaluación de desempeño (primero seleccionar persona, luego formulario)
    previsualizar = False

    agentes_ref = db.collection("agentes").where("evaluado_2025", "==", False).stream()
    agentes = [{**doc.to_dict(), "id": doc.id} for doc in agentes_ref]
    agentes_ordenados = sorted(agentes, key=lambda x: x["apellido_nombre"])

    if not agentes_ordenados:
        st.warning("⚠️ No hay agentes disponibles para evaluar en 2025.")
        st.stop()

    # Selección directa de agente
    nombres = [a["apellido_nombre"] for a in agentes_ordenados]
    seleccionado = st.selectbox("Seleccione un agente para evaluar", nombres, key="select_agente")
    agentes = get_agentes_para_evaluar()

    #traer datos de agentes
    if agente:
        cuil = agente["cuil"]
        apellido_nombre = agente["apellido_nombre"]
        nivel = agente.get("nivel", "")
        grado = agente.get("grado", "")
        unidad = agente.get("unidad", "")
        dependencia_simple = agente.get("dependencia_simple", "")
       
        # Mostrar selección de tipo de formulario
        tipo = st.selectbox(
            "Seleccione el tipo de formulario",
            options=[""] + list(formularios.keys()),
            format_func=lambda x: f"Formulario {x}" if x else "Seleccione una opción",
            key="select_tipo"
        )

        if tipo != "":
            if 'previsualizado' not in st.session_state:
                st.session_state.previsualizado = False
            if 'confirmado' not in st.session_state:
                st.session_state.confirmado = False

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
                tipo_formulario = tipo  # 👈 esto antes
                rango = clasificaciones.get(tipo_formulario, [])
                puntaje_maximo = max(p for bloque in formularios[tipo_formulario] for _, p in bloque["opciones"]) * len(formularios[tipo_formulario])
                resultado_absoluto = round(total / puntaje_maximo, 4)
                clasificacion = next(
                    (nombre for nombre, maxv, minv in rango if minv <= total <= maxv),
                    "Sin clasificación"
                )

                st.markdown("---")
                st.markdown(f"### 📊 Puntaje: {total}")
                st.markdown(f"### 📌 Calificación: **{clasificacion}**")
                st.markdown("---")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Sí, enviar evaluación"):
                        st.session_state.confirmado = True
                        tipo_formulario = tipo
                        evaluacion_data = {
                            "apellido_nombre": apellido_nombre,
                            "cuil": cuil,
                            "anio": 2025,
                            "formulario": tipo_formulario,
                            "puntaje_total": total,
                            "evaluacion": clasificacion,
                            "evaluado_2025": True,
                            "factor_puntaje": factor_puntaje,
                            "puntaje_maximo": puntaje_maximo,
                            "nivel": nivel,
                            "grado": grado,
                            "unidad": unidad,                         
                            "dependencia_simple": dependencia_simple,
                            "resultado_absoluto": resultado_absoluto,                            
                            "timestamp": firestore.SERVER_TIMESTAMP,                            
                        }

                        doc_id = f"{cuil}-2025"
                        db.collection("evaluaciones").document(doc_id).set(evaluacion_data)
                        db.collection("agentes").document(cuil).update({"evaluado_2025": True})

                        st.success(f"📤 Evaluación de {apellido_nombre} enviada correctamente")
                        st.balloons()
                        time.sleep(2)

                        # Eliminar solo las claves necesarias
                        for key in list(st.session_state.keys()):
                            if key.startswith("factor_") or key in ["select_tipo", "previsualizado", "confirmado", "puntajes", "respuestas_completas", "last_tipo", "select_agente"]:
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

elif opcion == "📋 Evaluaciones":
    evaluaciones = get_evaluaciones()

    if not evaluaciones:
        st.info("No hay evaluaciones registradas.")
    else:
        df_eval = pd.DataFrame(evaluaciones)
        st.dataframe(df_eval[["apellido_nombre", "anio", "formulario", "puntaje_total", "evaluacion"]], use_container_width=True)




elif opcion == "EVALUACIÓN GENERAL":
    evaluaciones = get_evaluaciones()

    if not evaluaciones:
        st.info("No hay evaluaciones registradas.")
    else:
        df_eval = pd.DataFrame(evaluaciones)
        st.dataframe(df_eval[["apellido_nombre", "anio", "formulario", "puntaje_total", "evaluacion"]], use_container_width=True)





