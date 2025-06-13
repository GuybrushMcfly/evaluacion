import streamlit as st
import pandas as pd
import yaml
from datetime import date
import time

def cargar_formularios():
    with open("formularios.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["formularios"], config["clasificaciones"]

def mostrar(supabase, formularios, clasificaciones):
    st.markdown("<h1 style='font-size:24px;'>📄 Formulario de Evaluación</h1>", unsafe_allow_html=True)

    usuario_actual = st.session_state.get("usuario")

    agentes_data = supabase.table("agentes")\
        .select("cuil, apellido_nombre, ingresante, nivel, grado, dependencia, dependencia_general, activo, motivo_inactivo, fecha_inactivo")\
        .eq("evaluador_2024", usuario_actual)\
        .eq("evaluado_2024", False)\
        .order("apellido_nombre")\
        .execute().data

    # Verificar si hay agentes para evaluar
    if not agentes_data:
        st.warning("⚠️ No hay agentes disponibles para evaluar.")
        return
    
    # Selección de agente
    opciones_agentes = [a["apellido_nombre"] for a in agentes_data]
    seleccionado = st.selectbox("👤 Seleccione un agente para evaluar", opciones_agentes)
    agente = next((a for a in agentes_data if a["apellido_nombre"] == seleccionado), None)
    
    if not agente:
        return
    
    # Variables base
    cuil = agente["cuil"]
    apellido_nombre = agente["apellido_nombre"]
    
# Preparar datos del agente
    # Primera fila de información
    datos_fila1 = {
        "CUIL": cuil,
        "Apellido y Nombre": apellido_nombre,
        "NIVEL": agente.get("nivel", ""),
        "GRADO": agente.get("grado", "")
    }
    
    # Segunda fila de información
    datos_fila2 = {
        "TRAMO": agente.get("tramo", ""),
        "AGRUPAMIENTO": agente.get("agrupamiento", ""),
        "INGRESANTE": "Sí" if agente.get("ingresante") else "No",
        "ULT. CALIFICACIÓN": agente.get("ultima_calificacion", "")
    }
    
    # Tercera fila si hay inactividad
    if not agente.get("activo", True):
        datos_fila3 = {
            "ACTIVO": "No",
            "MOTIVO INACTIVIDAD": agente.get("motivo_inactivo", ""),
            "FECHA BAJA": agente.get("fecha_inactivo", ""),
            "CALIF. CORRIMIENTO": agente.get("calificaciones_corrimiento", "")
        }
        df_info = pd.DataFrame([datos_fila1, datos_fila2, datos_fila3])
    else:
        # Agregar calificación de corrimiento a la segunda fila
        datos_fila2["CALIF. CORRIMIENTO"] = agente.get("calificaciones_corrimiento", "")
        df_info = pd.DataFrame([datos_fila1, datos_fila2])
    
    # Mostrar tabla
    st.dataframe(df_info, use_container_width=True, hide_index=True)
    
    # Selección de tipo de formulario
    tipo = st.selectbox(
        "📄 Seleccione el tipo de formulario",
        options=[""] + list(formularios.keys()),
        format_func=lambda x: f"Formulario {x} - {formularios[x]['titulo']}" if x else "Seleccione una opción",
        key="select_tipo"
    )


    if tipo == "":
        return

    if 'previsualizado' not in st.session_state:
        st.session_state.previsualizado = False
    if 'confirmado' not in st.session_state:
        st.session_state.confirmado = False

    with st.form("form_eval"):
        factor_puntaje = {}
        factor_posicion = {}
        puntajes = []
        respuestas_completas = True

        for i, bloque in enumerate(formularios[tipo]['factores']):
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
                posicion = opciones.index(seleccion) + 1
                factor_posicion[f"Factor {clave}"] = posicion
            else:
                respuestas_completas = False

        previsualizar = st.form_submit_button("🔍 Previsualizar calificación")

    if previsualizar:
        if respuestas_completas:
            st.session_state.update({
                "previsualizado": True,
                "puntajes": puntajes,
                "respuestas_completas": True,
                "factor_puntaje": factor_puntaje,
                "factor_posicion": factor_posicion
            })
        else:
            st.error("❌ Complete todas las respuestas para previsualizar la calificación")
            st.session_state.previsualizado = False

    if st.session_state.get("previsualizado") and st.session_state.get("respuestas_completas"):
        total = sum(st.session_state.puntajes)
        rango = clasificaciones.get(tipo, [])
        clasificacion = next((nombre for nombre, maxv, minv in rango if minv <= total <= maxv), "Sin clasificación")

        st.markdown("---")
        st.markdown(f"### 📊 Puntaje preliminar: {total}")
        st.markdown(f"### 📌 Calificación estimada: **{clasificacion}**")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Sí, enviar evaluación"):
                tipo_formulario = tipo
                evaluador = st.session_state.get("usuario", "desconocido")
                puntaje_maximo = max(puntajes) * len(puntajes) if puntajes else None
                puntaje_relativo = round((total / puntaje_maximo) * 10, 3) if puntaje_maximo else None

                unidad_info = supabase.table("unidades_evaluacion")\
                    .select("unidad_evaluadora, unidad_analisis, dependencia_general")\
                    .eq("dependencia", agente.get("dependencia"))\
                    .maybe_single().execute().data

                supabase.table("evaluaciones").insert({
                    "cuil": cuil,
                    "apellido_nombre": apellido_nombre,
                    "nivel": agente.get("nivel"),
                    "grado": agente.get("grado"),
                    "dependencia": agente.get("dependencia"),
                    "dependencia_general": unidad_info.get("dependencia_general") if unidad_info else None,
                    "unidad_evaluadora": unidad_info.get("unidad_evaluadora") if unidad_info else None,
                    "unidad_analisis": unidad_info.get("unidad_analisis") if unidad_info else None,
                    "anio_evaluacion": 2024,
                    "evaluador": evaluador,
                    "formulario": tipo_formulario,
                    "factor_puntaje": st.session_state["factor_puntaje"],
                    "factor_posicion": st.session_state["factor_posicion"],
                    "puntaje_total": total,
                    "puntaje_maximo": puntaje_maximo,
                    "puntaje_relativo": puntaje_relativo,
                    "calificacion": clasificacion,
                    "fecha_notificacion": date.today().isoformat(),
                    "activo": agente.get("activo"),
                    "motivo_inactivo": agente.get("motivo_inactivo"),
                    "fecha_inactivo": agente.get("fecha_inactivo"),
                }).execute()

                supabase.table("agentes").update({"evaluado_2024": True}).eq("cuil", cuil).execute()

                st.success(f"📤 Evaluación de {apellido_nombre} enviada correctamente")
                st.balloons()
                time.sleep(2)

                for key in list(st.session_state.keys()):
                    if key.startswith("factor_") or key in ["select_tipo", "previsualizado", "confirmado", "puntajes", "respuestas_completas", "last_tipo"]:
                        del st.session_state[key]

                st.rerun()

        with col2:
            if st.button("❌ No, revisar opciones"):
                st.session_state["previsualizado"] = False
                st.warning("🔄 Por favor revise las opciones seleccionadas")

    st.session_state["last_tipo"] = tipo
