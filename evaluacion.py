import streamlit as st

## ---- CONFIGURACIÓN DE PÁGINA ----
st.set_page_config(page_title="Evaluación de Desempeño", layout="wide")

from supabase import create_client, Client
import pandas as pd
import time
import yaml
from yaml.loader import SafeLoader
from sqlalchemy import create_engine
import streamlit_authenticator as stauth
import psycopg2
import datetime
from datetime import date


# ───── CONEXIÓN ─────
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    #key = st.secrets["SUPABASE_KEY"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    
    return create_client(url, key)

supabase = init_connection()

# ───── CONSULTA ─────
#@st.cache_data(ttl=600)
def obtener_agentes():
    result = supabase.table("agentes").select("*").limit(10).execute()
    return result.data if result.data else []



# ---- OBTENER USUARIOS DESDE SUPABASE ----
usuarios = supabase.table("usuarios_evaluadores")\
    .select("usuario, password, apellido_nombre, rol")\
    .eq("activo", True)\
    .execute().data

credentials = {"usernames": {}}
for u in usuarios:
    credentials["usernames"][u["usuario"]] = {
        "name": u["apellido_nombre"],
        "password": u["password"],
        "email": "",
        "rol": u.get("rol", {})
    }


# ---- AUTENTICACIÓN ----
authenticator = stauth.Authenticate(
    credentials=credentials,
    cookie_name="evaluacion_app",
    cookie_key="clave_segura_super_oculta",
    cookie_expiry_days=1
)


name, authentication_status, username = authenticator.login()

if authentication_status:
    st.session_state["usuario"] = username
    st.sidebar.success(f"Hola, {name}")
    authenticator.logout("Cerrar sesión", "sidebar")
    st.markdown("""<h1 style='font-size: 30px; color: white;'>📊 Evaluación de Desempeño</h1>""", unsafe_allow_html=True)
elif authentication_status is False:
    st.error("❌ Usuario o contraseña incorrectos.")
    st.stop()
elif authentication_status is None:
    st.warning("🔐 Ingresá tus credenciales para acceder al dashboard.")
    st.stop()


# ---- CARGAR FORMULARIOS ----
with open("formularios.yaml", "r", encoding="utf-8") as f:
    config_formularios = yaml.safe_load(f)
    formularios = config_formularios["formularios"]
    clasificaciones = config_formularios["clasificaciones"]

# ---- NAVEGACIÓN ----
opcion = st.sidebar.radio("📂 Navegación", ["📝 Instructivo", "📄 Formulario", "📋 Evaluaciones", "✏️ Editar nombres"])

if opcion == "📝 Instructivo":
    st.title("📝 Instructivo")
    st.markdown("""
    Bienvenido al sistema de Evaluación de Desempeño.  
    1. Seleccioná el formulario correspondiente.  
    2. Completá todos los factores.  
    3. Previsualizá y confirmá la evaluación.  
    """)


elif opcion == "📄 Formulario":

    st.markdown("""
        <style>
        /* Solo afecta radios dentro del formulario principal */
        div[data-testid="stForm"] div[role="radiogroup"] > label {
            padding: 10px 15px;
            margin: 8px 0;  /* Aumenté un poco más el margen */
            border-radius: 8px;
            transition: all 0.2s;
        }
        
     
        
        /* Restablece estilos para la sidebar */
        section[data-testid="stSidebar"] div[role="radiogroup"] > label {
            padding: initial;
            margin: initial;
            border-radius: initial;
        }
        </style>
    """, unsafe_allow_html=True)


    # Obtener lista de agentes desde Supabase con campo ingresante
    usuario_actual = st.session_state.get("usuario")
    agentes_data = supabase.table("agentes")\
        .select("cuil, apellido_nombre, ingresante")\
        .eq("evaluador_2025", usuario_actual)\
        .eq("evaluado_2025", False)\
        .order("apellido_nombre")\
        .execute().data
    
    if not agentes_data:
        st.warning("⚠️ No hay agentes disponibles para evaluar.")
        st.stop()
    
    # Selector de agente
    opciones_agentes = [a["apellido_nombre"] for a in agentes_data]
    seleccionado = st.selectbox("👤 Seleccione un agente para evaluar", opciones_agentes)

    # Obtener agente seleccionado
    agente = next((a for a in agentes_data if a["apellido_nombre"] == seleccionado), None)

    if agente:
        cuil = agente["cuil"]
        apellido_nombre = agente["apellido_nombre"]
        ingresante = agente.get("ingresante", False)

        # Mostrar datos del agente en tabla editable (sin índice)
        df_info = pd.DataFrame([{
            "CUIL": cuil,
            "Apellido y Nombre": apellido_nombre,
            "Ingresante": ingresante
        }])

        editado = st.data_editor(
            df_info,
            column_config={
                "Ingresante": st.column_config.CheckboxColumn("Ingresante")
            },
            hide_index=True,
            disabled=["CUIL", "Apellido y Nombre"],
            use_container_width=True
        )

        nuevo_ingresante = editado["Ingresante"].iloc[0]
        if nuevo_ingresante != ingresante:
            supabase.table("agentes").update({"ingresante": bool(nuevo_ingresante)}).eq("cuil", cuil).execute()
            st.success("✅ Valor de ingresante actualizado.")

        # Selector de formulario
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
            factor_posicion = {}
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
                    #factor_posicion[f"Factor {clave}"] = seleccion 
                    # Buscar la posición de la opción seleccionada en la lista
                    posicion = opciones.index(seleccion) + 1
                    factor_posicion[f"Factor {clave}"] = posicion
                   
                else:
                    respuestas_completas = False

            previsualizar = st.form_submit_button("🔍 Previsualizar calificación")

        if previsualizar:
            if respuestas_completas:
                st.session_state.previsualizado = True
                st.session_state.puntajes = puntajes
                st.session_state.respuestas_completas = True

                st.session_state.factor_puntaje = factor_puntaje#verver
                st.session_state.factor_posicion = factor_posicion#verver
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


                    # Extraer más datos del agente (si están en Supabase)
                    nivel = agente.get("nivel")
                    grado = agente.get("grado")
                    dependencia = agente.get("dependencia")
                    dependencia_general = agente.get("dependencia_general")
                    unidad_evaluadora = agente.get("unidad_evaluadora")
                    unidad_analisis = agente.get("unidad_analisis")
                    
                    # Evaluador desde sesión
                    evaluador = st.session_state.get("usuario", "desconocido")
                    
                    # Cálculo adicional
                    puntaje_maximo = max(puntajes) * len(puntajes) if puntajes else None
                    puntaje_relativo = round((total / puntaje_maximo) * 10, 3) if puntaje_maximo else None

                                    
                    # Insertar en Supabase
                    supabase.table("evaluaciones").insert({
                        "cuil": cuil,
                        "nivel": nivel,
                        "grado": grado,
                        "dependencia": dependencia,
                        "dependencia_general": dependencia_general,
                        "unidad_evaluadora": unidad_evaluadora,
                        "unidad_analisis": unidad_analisis,
                        "anio_evaluacion": 2025,
                        "evaluador": evaluador,
                        "formulario": tipo_formulario,
                        #"factor_puntaje": factor_puntaje,
                        #"factor_posicion": factor_posicion,
                        "factor_puntaje": st.session_state.get("factor_puntaje", {}),
                        "factor_posicion": st.session_state.get("factor_posicion", {}),
                        "puntaje_total": total,
                        "puntaje_maximo": puntaje_maximo,
                        "puntaje_relativo": puntaje_relativo,
                        "calificacion": clasificacion,
                    #    "fecha_notificacion": date.today()
                        "fecha_notificacion": date.today().isoformat()

                    }).execute()
                                        
                   
                    
                    # Marcar como evaluado en la tabla 'agentes'
                    #supabase.table("agentes").update({
                    #    "evaluado_2025": True
                    #}).eq("cuil", cuil).execute()

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

elif opcion == "📋 Evaluaciones":
    st.header("📋 Evaluaciones realizadas")

    # Obtener evaluaciones y agentes
    evaluaciones = supabase.table("evaluaciones").select("*").execute().data
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").execute().data
    mapa_agentes = {a["cuil"]: a["apellido_nombre"] for a in agentes}

    if not evaluaciones:
        st.info("No hay evaluaciones registradas.")
    else:
        filas = []
        for e in evaluaciones:
            cuil = e["cuil"]
            agente = mapa_agentes.get(cuil, "Desconocido")
    
            # FORMULARIO
            formulario = e.get("formulario", "")
    
            # FACTOR PUNTAJE
            factores_puntaje = e.get("factor_puntaje", {})
            factores_formateados = {}
            for k, v in factores_puntaje.items():
                if not k.startswith("Factor "):
                    partes = k.split('. ')
                    clave = partes[0].strip()
                    k = f"Factor {clave}"
                factores_formateados[k] = v
            resumen_puntaje = ", ".join([f"{k} ({v})" for k, v in factores_formateados.items()])
    
            # FACTOR POSICION
            factores_posicion = e.get("factor_posicion", {})
            posiciones_formateadas = {}
            for k, v in factores_posicion.items():
                if not k.startswith("Factor "):
                    partes = k.split('. ')
                    clave = partes[0].strip()
                    k = f"Factor {clave}"
                posiciones_formateadas[k] = v
            resumen_posicion = ", ".join([f"{k} ({v})" for k, v in posiciones_formateadas.items()])
    
            # CALIFICACIÓN Y PUNTAJES
            calificacion = e.get("calificacion", "")
            total = e.get("puntaje_total", "")
            maximo = e.get("puntaje_maximo", "")
            relativo = e.get("puntaje_relativo", "")
    
            # Construir fila final
            filas.append({
                "CUIL": cuil,
                "AGENTE": agente,
                "FORMULARIO": formulario,
                "FACTOR/POSICION": resumen_posicion,
                "FACTOR/PUNTAJE": resumen_puntaje,
                "CALIFICACION": calificacion,
                "PUNTAJE TOTAL": total,
                "PUNTAJE MÁXIMO": maximo,
                "PUNTAJE RELATIVO": relativo
            })
    
        df_resumen = pd.DataFrame(filas)
        st.dataframe(df_resumen, use_container_width=True)


        import io
        
        # Crear buffer en memoria
        buffer = io.BytesIO()
        
        # Guardar DataFrame como archivo .xlsx en el buffer
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_resumen.to_excel(writer, index=False, sheet_name='Evaluaciones')
        
        # Preparar botón de descarga
        st.download_button(
            label="📥 Descargar en Excel",
            data=buffer.getvalue(),
            file_name="evaluaciones.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


elif opcion == "✏️ Editar nombres":
    st.header("✏️ Editar nombres de agentes")

    # Traer datos
    agentes = supabase.table("agentes").select("cuil, apellido_nombre").order("apellido_nombre").execute().data

    if not agentes:
        st.info("No hay agentes cargados.")
        st.stop()

    df_agentes = pd.DataFrame(agentes)[["cuil", "apellido_nombre"]]

    # Mostrar tabla editable directamente
    editado = st.data_editor(
        df_agentes,
        hide_index=True,
        column_config={"apellido_nombre": "Apellido y Nombre"},
        disabled=["cuil"],
        use_container_width=True
    )

    # Detectar cambios y actualizar
    if st.button("💾 Guardar cambios"):
        cambios = editado[editado["apellido_nombre"] != df_agentes["apellido_nombre"]]
        for _, fila in cambios.iterrows():
            supabase.table("agentes").update(
                {"apellido_nombre": fila["apellido_nombre"]}
            ).eq("cuil", fila["cuil"]).execute()
        st.success("✅ Cambios guardados exitosamente.")
        time.sleep(1)
        st.rerun()





