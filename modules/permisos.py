import streamlit as st

def rol_usuario() -> dict:
    """Devuelve el diccionario de roles del usuario autenticado."""
    return st.session_state.get("rol", {})

def es_coordinador() -> bool:
    return rol_usuario().get("coordinador", False)

def es_rrhh() -> bool:
    return rol_usuario().get("rrhh", False)

def es_evaluador_general() -> bool:
    return rol_usuario().get("evaluador_general", False)

def es_evaluador() -> bool:
    return rol_usuario().get("evaluador", False)

def puede_ver_rrhh() -> bool:
    return es_rrhh() or es_coordinador()

def puede_ver_formulario() -> bool:
    return es_evaluador() or es_evaluador_general() or es_rrhh() or es_coordinador()

def puede_editar() -> bool:
    return es_coordinador()

def puede_configurar() -> bool:
    return es_coordinador()
