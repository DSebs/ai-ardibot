import streamlit as st
import base64
from chatbot.rag_engine import ask, ingest
import os
import time
from PIL import Image
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                   format="%(asctime)s [%(levelname)s] %(message)s",
                   handlers=[logging.FileHandler("app.log"), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Inicializar caché de sesión para mejorar rendimiento
if "history" not in st.session_state:
    st.session_state.history = []
if "response_times" not in st.session_state:
    st.session_state.response_times = []
if "model_loaded" not in st.session_state:
    st.session_state.model_loaded = False
if "error" not in st.session_state:
    st.session_state.error = None
if "submitted_query" not in st.session_state:
    st.session_state.submitted_query = ""
if "waiting_for_answer" not in st.session_state:
    st.session_state.waiting_for_answer = False
if "first_question_asked" not in st.session_state:
    st.session_state.first_question_asked = False

# Función para manejar la consulta
def handle_submit():
    if st.session_state.query_input:
        st.session_state.submitted_query = st.session_state.query_input
        st.session_state.waiting_for_answer = True
        # Marcar que ya se hizo la primera pregunta
        st.session_state.first_question_asked = True
        # Limpiar el input
        st.session_state.query_input = ""

# Cargar favicon
favicon_path = os.path.join("chatbot", "assets", "FaviconArdy.png")
favicon = Image.open(favicon_path) if os.path.exists(favicon_path) else None

# 📐 Configuración de la página
st.set_page_config(
    page_title="ArdyBot",
    page_icon=favicon,
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Cargar imágenes (una vez usando caché)
@st.cache_data
def get_image_base64(img_path):
    try:
        if os.path.exists(img_path):
            return base64.b64encode(open(img_path, "rb").read()).decode()
        return None
    except Exception as e:
        logger.error(f"Error al cargar imagen: {str(e)}")
        return None

# Cargar imágenes
banner_path = os.path.join("chatbot", "assets", "Ardy_Banner.png")
watermark_path = os.path.join("chatbot", "assets", "Ardy_MA.png")
banner_base64 = get_image_base64(banner_path)
watermark_base64 = get_image_base64(watermark_path)

# CSS personalizado para mejorar rendimiento de UI y contraste
st.markdown(f"""
<style>
    body {{
        color: #FFFFFF;
        background-color: #0E1117;
        {f"background-image: url('data:image/png;base64,{watermark_base64}');" if st.session_state.first_question_asked and watermark_base64 else ""}
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
        background-opacity: 0.5;
    }}
    .main {{max-width: 900px; padding: 1rem;}}
    .stButton button {{width: 100%;}}
    
    /* Estilos para los mensajes */
    .message {{
        margin-bottom: 15px;
        max-width: 85%;
        clear: both;
    }}
    
    .user-message {{
        float: right;
        background-color: #2C5282;
        color: white;
        border-radius: 18px 18px 4px 18px;
        padding: 12px 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }}
    
    .bot-message {{
        float: left;
        background-color: #2D3748;
        color: white;
        border-radius: 18px 18px 18px 4px;
        padding: 12px 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }}
    
    /* Ocultar etiquetas de los campos de texto */
    .st-emotion-cache-1gulkj5 {{
        display: none;
    }}
</style>
""", unsafe_allow_html=True)

# Cabecera con imagen y título
if not st.session_state.first_question_asked:
    # Mostrar header completo con imagen grande antes de la primera pregunta
    if banner_base64:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 15px; margin-bottom: 20px;">
                <img src="data:image/png;base64,{banner_base64}" style="max-width: 100%; height: auto;" alt="ArdyBot Banner">
                <p style="font-size: 25px;">Tu asistente inteligente universitario 🏫</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="text-align: center; padding: 15px; margin-bottom: 20px;">
                <h1>ArdyBot 🐿️</h1>
                <p>Tu asistente inteligente universitario 🏫</p>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    # Mostrar header compacto después de la primera pregunta
    if banner_base64:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 10px; margin-bottom: 15px;">
                <img src="data:image/png;base64,{banner_base64}" style="max-width: 250px; height: auto;" alt="ArdyBot Banner">
                <p style="margin-bottom: 0;">Tu asistente universitario</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px; margin-bottom: 15px;">
                <h2>ArdyBot 🐿️</h2>
                <p style="margin-bottom: 0;">Tu asistente universitario</p>
            </div>
            """,
            unsafe_allow_html=True
        )

# 📘 Ingesta (opcional)
reglamento_path = os.path.join("data", "reglamento", "reglamento-universitario.pdf")
preguntas_path = os.path.join("data", "reglamento", "FAQArdyBot.pdf")
col1, col2 = st.columns([3, 1])

with col1:
    # Información sobre los documentos disponibles
    if not os.path.exists(reglamento_path) or not os.path.exists(preguntas_path):
        missing_docs = []
        if not os.path.exists(reglamento_path):
            missing_docs.append("Reglamento Universitario")
        if not os.path.exists(preguntas_path):
            missing_docs.append("Preguntas Frecuentes")
        st.error(f"Documentos no encontrados: {', '.join(missing_docs)}")
    else:
        with st.expander("ℹ️ Documentos de Conocimiento"):
            st.info("""
            **ArdyBot** utiliza los siguientes documentos para responder tus consultas:
            
            1. **Reglamento Universitario**: Contiene las normas y regulaciones oficiales de la Universidad.
            2. **Preguntas Frecuentes**: Versión actualizada con respuestas a preguntas comunes de los estudiantes.
            
            ¡Ahora ArdyBot es más inteligente! Puede responder preguntas tanto sobre el reglamento como sobre información general de la universidad.
            
            Si deseas reingestar los documentos, utiliza el botón "Reingestar Documentos" en el sidebar.
            """)

# Mostrar error si existe
if st.session_state.error:
    st.markdown(f"<div class='error-box'>**❌ Error:** {st.session_state.error}</div>", unsafe_allow_html=True)
    if st.button("🔄 Intentar nuevamente"):
        st.session_state.error = None
        st.session_state.waiting_for_answer = False
        st.rerun()

# Mostrar historial de mensajes
for q, a in st.session_state.history:
    # Mensaje del usuario
    st.markdown(
        f"""
        <div class="message user-message">
            <div>{q}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Mensaje del bot
    st.markdown(
        f"""
        <div class="message bot-message">
            <div>{a}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Barra de entrada para preguntas con botón de envío
col1, col2 = st.columns([6, 1])
with col1:
    st.text_input(
        label="Pregunta",
        key="query_input",
        placeholder="Escribe tu pregunta sobre la universidad o el reglamento...",
        on_change=handle_submit,
        label_visibility="collapsed"
    )
with col2:
    if st.button("→"):
        if st.session_state.query_input:
            handle_submit()
            st.rerun()

# Procesar nueva pregunta si hay una consulta pendiente
if st.session_state.waiting_for_answer and st.session_state.submitted_query:
    query = st.session_state.submitted_query
    with st.spinner(f"Ardy está pensando... 🐿️💭"):
        try:
            start_time = time.time()
            respuesta = ask(query)
            response_time = time.time() - start_time
            
            # Guardar en historial
            st.session_state.history.append((query, respuesta))
            st.session_state.response_times.append(response_time)
            
            # Mostrar tiempo de respuesta
            st.info(f"⏱️ Respuesta generada en {response_time:.2f} segundos")
            
            # Limpiar variables de estado
            st.session_state.error = None
            st.session_state.waiting_for_answer = False
            st.session_state.submitted_query = ""
            
            # Recargar para mostrar la nueva respuesta
            st.rerun()
        except Exception as e:
            logger.error(f"Error al procesar pregunta: {str(e)}", exc_info=True)
            st.session_state.error = str(e)
            st.error(f"Ha ocurrido un error: {str(e)}")
            st.session_state.waiting_for_answer = False
            st.session_state.submitted_query = ""

# Sidebar con estadísticas y opción para reingestar documentos
with st.sidebar:
    st.header("Estadísticas")
    if st.session_state.response_times:
        avg_time = sum(st.session_state.response_times) / len(st.session_state.response_times)
        last_time = st.session_state.response_times[-1]
        
        st.markdown(f"<div class='metric-box'>Última respuesta: {last_time:.2f}s</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box'>Tiempo promedio: {avg_time:.2f}s</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box'>Total de preguntas: {len(st.session_state.history)}</div>", unsafe_allow_html=True)
    
    # Mostrar historial reciente
    if st.session_state.history:
        st.header("Preguntas recientes")
        for i, (q, _) in enumerate(st.session_state.history[-5:]):
            st.markdown(f"**{i+1}.** {q[:40]}..." if len(q) > 40 else f"**{i+1}.** {q}")
    
    st.header("Opciones")
    # Botón para reingestar documentos
    if st.button("🔄 Reingestar Documentos"):
        with st.spinner("Reingestando documentos... Esto puede tomar un momento"):
            try:
                # Ingestar ambos documentos
                result = ingest(None)  # Esto procesará todos los PDF en data/reglamento/
                st.success(result)
                # Limpiar caché de respuestas
                st.session_state.history = []
                st.session_state.response_times = []
            except Exception as e:
                st.error(f"Error durante la ingestión: {str(e)}")
    
    # Botón para limpiar historial
    if st.session_state.history and st.button("🗑️ Limpiar historial"):
        st.session_state.history = []
        st.session_state.response_times = []
        st.session_state.first_question_asked = False
        st.rerun()

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; font-size: 13px; color: gray;'>"
    "Desarrollado con ❤️ por: <b>Santiago C., Sebastian D. y Juan Esteban R.</b><br>"
    "Universidad de Ibagué - 2025"
    "</div>",
    unsafe_allow_html=True
)

# JavaScript para hacer scroll automático al final del chat
if st.session_state.history:
    st.markdown("""
    <script>
        function scrollToBottom() {
            window.scrollTo(0, document.body.scrollHeight);
        }
        
        // Intentar varias veces ya que Streamlit puede cargar lentamente
        setTimeout(scrollToBottom, 500);
        setTimeout(scrollToBottom, 1000);
        setTimeout(scrollToBottom, 2000);
    </script>
    """, unsafe_allow_html=True)
