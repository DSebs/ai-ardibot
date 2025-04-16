import streamlit as st
import base64
from chatbot.rag_engine import ask, ingest
import os
from PIL import Image

# 📐 Configuración de la página
st.set_page_config(
    page_title="ArdyBot 🐿️",
    page_icon="🧠",
    layout="centered"
)

# 🖼️ Mostrar la imagen de Ardy
img_path = os.path.join("chatbot", "assets", "ardy.png")
if os.path.exists(img_path):
    st.markdown(
        f"""
        <div style='text-align: center;'>
            <img src='data:image/png;base64,{base64.b64encode(open(img_path, "rb").read()).decode()}'
                 width='320' style='margin-bottom: 20px;' />
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.error("❌ Imagen de Ardy no encontrada en chatbot/assets/ardy.png")
    
st.markdown("<h1 style='text-align: center;'>ArdyBot 🐿️</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Tu asistente inteligente del Reglamento Universitario 🏫</p>", unsafe_allow_html=True)
st.markdown("---")

# 📘 Ingesta (opcional)
pdf_path = os.path.join("data", "reglamento", "reglamento-universitario.pdf")
if not os.path.exists(pdf_path):
    st.error("No se encontró el reglamento. Asegúrate de que esté en data/reglamento/")
else:
    if st.button("🔄 Reprocesar documento"):
        with st.spinner("Procesando PDF y generando embeddings..."):
            ingest(pdf_path)
        st.success("¡Listo! Documento vectorizado.")

# 🧠 Entrada de pregunta
query = st.text_input("Haz tu pregunta sobre el reglamento universitario:", placeholder="¿Qué requisitos hay para cancelar una materia?")

# 📤 Resultado
if query:
    with st.spinner("Ardy está pensando... 🐿️💭"):
        respuesta = ask(query)
    st.markdown("### 🗨️ Respuesta:")
    st.success(respuesta)

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; font-size: 13px; color: gray;'>"
    "Desarrollado con ❤️ por: <b>Santiago C., Sebastian D. y Juan Esteban R.</b><br>"
    "Universidad de Ibagué - 2025"
    "</div>",
    unsafe_allow_html=True
)
