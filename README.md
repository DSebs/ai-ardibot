# ArdyBot

**ArdyBot** es un chatbot inteligente que responde preguntas relacionadas con el Reglamento Universitario de la Universidad de Ibagué. Utiliza tecnologías de Recuperación aumentada por generación (RAG) para interpretar preguntas en lenguaje natural y ofrecer respuestas precisas basadas en el contenido oficial del reglamento.

---

## 📝 Resumen

ArdyBot permite a los estudiantes consultar fácilmente las normas universitarias, como requisitos de cancelación de materias, tipos de estudiantes, entre otros, a través de una interfaz conversacional amigable. 

---

## ✨ Características

- ✅ Ingesta automática del reglamento en PDF.
- 💬 Interfaz tipo chat con diseño amigable.
- 📦 Reprocesamiento del documento con un solo clic.
- 🧠 Respuestas generadas con RAG (Retrieval-Augmented Generation).
- 🎨 Imagen personalizada de Ardy (mascota oficial de la universidad).
- ⚙️ Interfaz gráfica construida en Streamlit.

---

## 🛠️ Tecnologías

- `LangChain` – Construcción del motor RAG.
- `ChromaDB` – Almacenamiento vectorial.
- `FastEmbed` – Embeddings rápidos para búsqueda semántica.
- `Streamlit` – Interfaz gráfica interactiva.
- `Python 3.10+` – Lenguaje base del proyecto.

---

## 🚀 Modo de uso

1. Clona el repositorio:
   ```bash
   git clone https://github.com/DSebs/ai-ardibot.git
   cd ai-ardibot
   ```

2. Crea un entorno virtual y actívalo:
   ```bash
   python -m venv venv
   # En Windows
   venv\Scripts\activate
   # En Linux/Mac
   source venv/bin/activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Ejecuta el chatbot con interfaz:
   ```bash
   streamlit run chatbot/app.py
   ```

5. Haz preguntas relacionadas con el reglamento y Ardy te responderá

## 📂 Estructura de directorios

Al ejecutar el chatbot por primera vez, se crearán automáticamente los siguientes directorios:

- `local_data/` - Directorio que contiene datos locales no versionados en git
  - `chroma_db/` - Base de datos vectorial de ChromaDB
  - `embedding_cache/` - Caché de embeddings para FastEmbed

Estos directorios contienen archivos grandes que no son adecuados para el control de versiones y se generan automáticamente al ejecutar la aplicación.

## 👥 Autores

Desarrollado con ❤️ por:

- Santiago Cardenas.
- Sebastián Diaz.
- Juan Esteban Rodriguez.

### Universidad de Ibagué – 2025

