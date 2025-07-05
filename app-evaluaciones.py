import streamlit as st
import json
from modules import auth
from views import instructivo, formularios, evaluaciones, rrhh, capacitacion, configuracion
import bcrypt

# Configuración de página (sin cambios)
st.set_page_config(page_title="Evaluación de Desempeño", layout="wide", initial_sidebar_state="expanded")

# ---- ESTILOS CSS PARA EL MENÚ ----
st.markdown("""
<style>
/* Estilo para el menú de navegación */
[data-testid="stSidebarNav"] {
    padding-top: 0.5rem;
}

/* Estilo para los items del menú */
[data-testid="stSidebarNav"] .nav-item {
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    margin: 0.25rem 0;
    transition: all 0.2s;
}

[data-testid="stSidebarNav"] .nav-item:hover {
    background-color: #f0f2f6;
}

[data-testid="stSidebarNav"] .nav-item[aria-current="page"] {
    background-color: #2563eb;
    color: white !important;
    font-weight: 600;
}

/* Logo en sidebar */
.sidebar-logo {
    margin-bottom: 1rem;
    padding: 0 1rem;
}
</style>
""", unsafe_allow_html=True)

# Logo en sidebar (sin cambios)
st.sidebar.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
st.sidebar.image("logo-cap.png", use_column_width=True)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# ---- AUTENTICACIÓN (sin cambios) ----
name, authentication_status, username, authenticator, supabase, cambiar_password = auth.cargar_usuarios_y_autenticar()

# ---- CAMBIO DE CONTRASEÑA FORZADO (sin cambios) ----
if cambiar_password:
    st.warning("🔐 Debe cambiar su contraseña para continuar.")
    st.markdown("**⚠️ Requisitos de la nueva contraseña:**\n- Mínimo 6 caracteres\n- Debe contener al menos un número")

    nueva = st.text_input("Nueva contraseña", type="password", key="nueva_password")
    repetir = st.text_input("Repetir contraseña", type="password", key="repetir_password")

    if nueva and repetir:
        if nueva != repetir:
            st.error("❌ Las contraseñas no coinciden.")
        elif not auth.contraseña_valida(nueva):
            st.error("❌ La contraseña debe tener al menos 6 caracteres y contener al menos un número.")
        elif st.button("Guardar nueva contraseña"):
            hashed = bcrypt.hashpw(nueva.encode(), bcrypt.gensalt()).decode()
            supabase.table("usuarios").update({
                "password": hashed,
                "cambiar_password": False
            }).eq("usuario", username).execute()

            st.success("✅ Contraseña actualizada correctamente.")
            st.rerun()

    st.stop()

elif authentication_status:
    # Cargar datos del usuario (sin cambios)
    try:
        usuario_data = supabase.table("usuarios")\
            .select("apellido_nombre, rol")\
            .eq("usuario", username)\
            .execute()\
            .data

        if usuario_data:
            rol_data = usuario_data[0].get("rol", {})
            if isinstance(rol_data, str):
                try:
                    rol_data = json.loads(rol_data)
                except json.JSONDecodeError:
                    rol_data = {}
            if not isinstance(rol_data, dict):
                rol_data = {}

            st.session_state.update({
                "usuario": username,
                "nombre_completo": usuario_data[0]['apellido_nombre'],
                "rol": rol_data
            })
        else:
            st.error("❌ No se pudieron cargar los datos del usuario.")
            st.stop()

    except Exception as e:
        st.error(f"❌ Error al cargar datos del usuario: {str(e)}")
        st.stop()

    if not st.session_state.get("usuario") or not st.session_state.get("rol"):
        st.warning("⚠️ La sesión ha expirado o es inválida. Por favor, vuelva a iniciar sesión.")
        authenticator.logout("Cerrar sesión", "sidebar")
        st.stop()

    # ---- INTERFAZ DE USUARIO (sin cambios) ----
    st.sidebar.success(f"{st.session_state['nombre_completo']}")
    authenticator.logout("Cerrar sesión", "sidebar")
    st.sidebar.markdown("---")

    # ---- NAVEGACIÓN MODERNA (adaptación del menú) ----
    rol = st.session_state.get("rol", {})
    
    # Definir páginas disponibles según rol
    pages = []
    
    # Página de Instructivo (disponible para todos)
    pages.append(st.Page(
        lambda: instructivo.mostrar(supabase), 
        title="📝 Instructivo", 
        icon="📝"
    ))
    
    # Páginas para evaluadores
    if rol.get("evaluador") or rol.get("evaluador_general"):
        formularios_data, clasificaciones_data = formularios.cargar_formularios()
        
        pages.append(st.Page(
            lambda: formularios.mostrar(supabase, formularios_data, clasificaciones_data), 
            title="📄 Formularios", 
            icon="📄"
        ))
        
        pages.append(st.Page(
            lambda: evaluaciones.mostrar(supabase), 
            title="📋 Evaluaciones", 
            icon="📋"
        ))
    
    # Páginas para RRHH
    if rol.get("rrhh"):
        pages.append(st.Page(
            lambda: rrhh.mostrar(supabase), 
            title="👥 RRHH", 
            icon="👥"
        ))
    
    # Páginas para coordinadores
    if rol.get("coordinador"):
        pages.append(st.Page(
            lambda: capacitacion.mostrar(supabase), 
            title="📘 Capacitación", 
            icon="📘"
        ))
        
        pages.append(st.Page(
            lambda: configuracion.mostrar(supabase), 
            title="⚙️ Configuración", 
            icon="⚙️"
        ))
    
    # Mostrar navegación y ejecutar página seleccionada
    current_page = st.navigation(
        pages,
        position="sidebar",
        expanded=True
    )
    current_page.run()
else:
    st.warning("Por favor inicie sesión")
