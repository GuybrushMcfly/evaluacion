import streamlit as st
import json
from modules import auth
from views import instructivo, formularios, evaluaciones, rrhh, capacitacion, configuracion
import bcrypt

# Configuración de página
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

# Logo en sidebar (corregido use_column_width -> use_container_width)
st.sidebar.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
st.sidebar.image("logo-cap.png", use_container_width=True)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# ---- AUTENTICACIÓN ----
name, authentication_status, username, authenticator, supabase, cambiar_password = auth.cargar_usuarios_y_autenticar()

# ---- CAMBIO DE CONTRASEÑA FORZADO ----
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

elif authentication_status is False:
    # Mostrar mensaje de error si la autenticación falló
    st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

elif authentication_status:
    # Cargar datos del usuario
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

    # ---- INTERFAZ DE USUARIO ----
    st.sidebar.success(f"{st.session_state['nombre_completo']}")
    authenticator.logout("Cerrar sesión", "sidebar")
    st.sidebar.markdown("---")

    # ---- NAVEGACIÓN ALTERNATIVA (por si st.navigation falla) ----
    opciones_menu = []
    funciones_menu = []
    
    # Página de Instructivo (disponible para todos)
    opciones_menu.append("📝 Instructivo")
    funciones_menu.append(lambda: instructivo.mostrar(supabase))
    
    # Páginas para evaluadores
    if rol.get("evaluador") or rol.get("evaluador_general"):
        formularios_data, clasificaciones_data = formularios.cargar_formularios()
        opciones_menu.append("📄 Formularios")
        funciones_menu.append(lambda: formularios.mostrar(supabase, formularios_data, clasificaciones_data))
        opciones_menu.append("📋 Evaluaciones")
        funciones_menu.append(lambda: evaluaciones.mostrar(supabase))
    
    # Páginas para RRHH
    if rol.get("rrhh"):
        opciones_menu.append("👥 RRHH")
        funciones_menu.append(lambda: rrhh.mostrar(supabase))
    
    # Páginas para coordinadores
    if rol.get("coordinador"):
        opciones_menu.append("📘 Capacitación")
        funciones_menu.append(lambda: capacitacion.mostrar(supabase))
        opciones_menu.append("⚙️ Configuración")
        funciones_menu.append(lambda: configuracion.mostrar(supabase))

    # Mostrar menú de navegación alternativo
    if rol.get("evaluador") or rol.get("evaluador_general"):
        indice_default = opciones_menu.index("📄 Formularios")
    elif rol.get("coordinador"):
        indice_default = opciones_menu.index("📘 Capacitación")
    else:
        indice_default = 0

    opcion = st.sidebar.radio("📂 Navegación", opciones_menu, index=indice_default)
    funciones_menu[opciones_menu.index(opcion)]()
else:
    st.warning("Por favor inicie sesión")
