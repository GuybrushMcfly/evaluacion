import streamlit as st
import json
from modules import auth
from views import instructivo, formularios, evaluaciones, rrhh, capacitacion, configuracion
import bcrypt

# Configuración de página
st.set_page_config(page_title="Evaluación de Desempeño", layout="wide", initial_sidebar_state="expanded")

# ---- ESTILOS CSS ----
st.markdown("""
<style>
/* Estilos para el sidebar */
[data-testid="stSidebar"] {
    background-color: #f8f9fa;
}

/* Estilos para los items del menú */
.stRadio > div > div {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.stRadio > div > div > label {
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    transition: all 0.2s;
}

.stRadio > div > div > label:hover {
    background-color: #e9ecef;
}

.stRadio > div > div > label > div:first-child {
    padding-left: 0.5rem;
}

/* Estilo para el item seleccionado */
.stRadio > div > div > [data-testid="stMarkdownContainer"]:has(> p > div:has(> input:checked)) {
    background-color: #0d6efd;
    color: white !important;
    font-weight: bold;
}

/* Logo */
.sidebar-logo {
    padding: 1rem;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# Logo en sidebar
with st.sidebar:
    st.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
    st.image("logo-cap.png", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

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
                "rol": rol_data or {}  # Aseguramos que rol siempre sea un dict
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
    with st.sidebar:
        st.success(f"👤 {st.session_state['nombre_completo']}")
        authenticator.logout("Cerrar sesión")
        st.markdown("---")

        # ---- NAVEGACIÓN ----
        opciones_menu = ["📝 Instructivo"]
        funciones_menu = [lambda: instructivo.mostrar(supabase)]

        # Verificar roles correctamente
        rol = st.session_state.get("rol", {})
        
        if rol.get("evaluador") or rol.get("evaluador_general"):
            formularios_data, clasificaciones_data = formularios.cargar_formularios()
            opciones_menu.extend(["📄 Formularios", "📋 Evaluaciones"])
            funciones_menu.extend([
                lambda: formularios.mostrar(supabase, formularios_data, clasificaciones_data),
                lambda: evaluaciones.mostrar(supabase)
            ])

        if rol.get("rrhh"):
            opciones_menu.append("👥 RRHH")
            funciones_menu.append(lambda: rrhh.mostrar(supabase))

        if rol.get("coordinador"):
            opciones_menu.extend(["📘 Capacitación", "⚙️ Configuración"])
            funciones_menu.extend([
                lambda: capacitacion.mostrar(supabase),
                lambda: configuracion.mostrar(supabase)
            ])

        # Selección de página
        if rol.get("evaluador") or rol.get("evaluador_general"):
            indice_default = opciones_menu.index("📄 Formularios") if "📄 Formularios" in opciones_menu else 0
        elif rol.get("coordinador"):
            indice_default = opciones_menu.index("📘 Capacitación") if "📘 Capacitación" in opciones_menu else 0
        else:
            indice_default = 0

        opcion = st.radio(
            "📂 Navegación",
            opciones_menu,
            index=indice_default,
            label_visibility="collapsed"
        )

    # Mostrar la página seleccionada
    funciones_menu[opciones_menu.index(opcion)]()
