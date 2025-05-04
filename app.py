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

# Función para manejar la consulta
def handle_submit():
    if st.session_state.query_input:
        st.session_state.submitted_query = st.session_state.query_input
        st.session_state.waiting_for_answer = True
        # Limpiar el input
        st.session_state.query_input = ""

# 📐 Configuración de la página
st.set_page_config(
    page_title="ArdyBot 🐿️",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS personalizado para mejorar rendimiento de UI y contraste
st.markdown("""
<style>
    body {
        color: #FFFFFF;
        background-color: #0E1117;
    }
    .main {max-width: 900px; padding: 1rem;}
    .stButton button {width: 100%;}
    .response-box {
        border-radius: 10px;
        padding: 15px;
        background-color: #2E3D4C;
        color: #FFFFFF;
        margin-bottom: 10px;
        border: 1px solid #3E5166;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .response-box strong {
        color: #E0E0E0;
        font-weight: bold;
    }
    .error-box {
        border-radius: 10px;
        padding: 15px;
        background-color: #5A2D2D;
        color: #FFFFFF;
        margin-bottom: 10px;
        border: 1px solid #7C3A3A;
    }
    .metric-box {
        background-color: #2D3A4A;
        color: #FFFFFF;
        border-radius: 5px;
        padding: 8px;
        margin: 5px 0;
        text-align: center;
        font-size: 14px;
        border: 1px solid #3E5166;
    }
    .stTextInput>div>div>input {
        background-color: #1E2A38;
        color: #FFFFFF;
        border: 1px solid #3E5166;
    }
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #FFFFFF;
    }
    div.user-question {
        color: #B8C7E5;
        margin-bottom: 5px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# 🖼️ Mostrar la imagen de Ardy (cargar solo una vez usando caché)
@st.cache_data
def get_image_base64(img_path):
    try:
        if os.path.exists(img_path):
            return base64.b64encode(open(img_path, "rb").read()).decode()
        return None
    except Exception as e:
        logger.error(f"Error al cargar imagen: {str(e)}")
        return None

img_path = os.path.join("chatbot", "assets", "ardy.png")
img_base64 = get_image_base64(img_path)

if img_base64:
    st.markdown(
        f"""
        <div style='text-align: center;'>
            <img src='data:image/png;base64,{img_base64}'
                 width='280' style='margin-bottom: 10px;' />
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.info("🐿️ Imagen de Ardy no disponible, pero el servicio funciona normalmente.")
    
st.markdown("<h1 style='text-align: center;'>ArdyBot 🐿️</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Tu asistente inteligente del Reglamento Universitario 🏫</p>", unsafe_allow_html=True)
st.markdown("---")

# Sidebar con estadísticas
with st.sidebar:
    st.header("📊 Estadísticas")
    if st.session_state.response_times:
        avg_time = sum(st.session_state.response_times) / len(st.session_state.response_times)
        last_time = st.session_state.response_times[-1]
        
        st.markdown(f"<div class='metric-box'>Última respuesta: {last_time:.2f}s</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box'>Tiempo promedio: {avg_time:.2f}s</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box'>Total de preguntas: {len(st.session_state.history)}</div>", unsafe_allow_html=True)
    
    # Mostrar historial reciente
    if st.session_state.history:
        st.header("🕒 Preguntas recientes")
        for i, (q, _) in enumerate(st.session_state.history[-5:]):
            st.markdown(f"**{i+1}.** {q[:40]}..." if len(q) > 40 else f"**{i+1}.** {q}")
    
    # Botón para limpiar historial
    if st.session_state.history and st.button("🧹 Limpiar historial"):
        st.session_state.history = []
        st.session_state.response_times = []
        st.rerun()

# 📘 Ingesta (opcional)
pdf_path = os.path.join("data", "reglamento", "reglamento-universitario.pdf")
col1, col2 = st.columns([3, 1])

with col1:
    # 🧠 Entrada de pregunta
    st.text_input("Haz tu pregunta sobre el reglamento universitario:", 
                key="query_input",
                placeholder="¿Qué requisitos hay para cancelar una materia?",
                on_change=handle_submit)

with col2:
    if not os.path.exists(pdf_path):
        st.error("Reglamento no encontrado")
    else:
        if st.button("🔄 Reprocesar PDF"):
            with st.spinner("Procesando documento..."):
                try:
                    start_time = time.time()
                    result = ingest(pdf_path)
                    process_time = time.time() - start_time
                    
                    if result and "Error" in result:
                        st.error(result)
                    else:
                        st.success(f"¡Listo en {process_time:.2f}s!")
                except Exception as e:
                    logger.error(f"Error al procesar PDF: {str(e)}", exc_info=True)
                    st.error(f"Error: {str(e)}")

# Mostrar error si existe
if st.session_state.error:
    st.markdown(f"<div class='error-box'>**❌ Error:** {st.session_state.error}</div>", unsafe_allow_html=True)
    if st.button("🔄 Intentar nuevamente"):
        st.session_state.error = None
        st.session_state.waiting_for_answer = False
        st.rerun()

# 📤 Mostrar diálogo de chat
st.markdown("### 💬 Conversación")
for q, a in st.session_state.history:
    st.markdown(f"<div class='user-question'>**🙋 Tú:** {q}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='response-box'><strong>🤖 Ardy:</strong> {a}</div>", unsafe_allow_html=True)

# Procesar nueva pregunta si hay una consulta pendiente
if st.session_state.waiting_for_answer and st.session_state.submitted_query:
    query = st.session_state.submitted_query
    with st.spinner(f"Ardy está pensando sobre: '{query}' 🐿️💭"):
        try:
            start_time = time.time()
            respuesta = ask(query)
            response_time = time.time() - start_time
            
            # Guardar en historial
            st.session_state.history.append((query, respuesta))
            st.session_state.response_times.append(response_time)
            
            # Mostrar la respuesta actual
            st.markdown(f"<div class='user-question'>**🙋 Tú:** {query}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='response-box'><strong>🤖 Ardy:</strong> {respuesta}</div>", unsafe_allow_html=True)
            st.info(f"⏱️ Respuesta generada en {response_time:.2f} segundos")
            
            # Limpiar variables de estado
            st.session_state.error = None
            st.session_state.waiting_for_answer = False
            st.session_state.submitted_query = ""
        except Exception as e:
            logger.error(f"Error al procesar pregunta: {str(e)}", exc_info=True)
            st.session_state.error = str(e)
            st.error(f"Ha ocurrido un error: {str(e)}")
            st.session_state.waiting_for_answer = False
            st.session_state.submitted_query = ""

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; font-size: 13px; color: gray;'>"
    "Desarrollado con ❤️ por: <b>Santiago C., Sebastian D. y Juan Esteban R.</b><br>"
    "Universidad de Ibagué - 2025"
    "</div>",
    unsafe_allow_html=True
)
