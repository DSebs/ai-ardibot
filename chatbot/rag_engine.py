from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.cache import InMemoryCache
from langchain.globals import set_llm_cache
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
import logging
import os
import time
import hashlib
import glob
import shutil

from .utils import load_and_split_pdf

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Habilitar caché para los LLMs
set_llm_cache(InMemoryCache())

# Caché de respuestas para consultas idénticas
RESPONSE_CACHE = {}
# Tamaño máximo de caché para evitar consumo excesivo de memoria
MAX_CACHE_SIZE = 100

# Directorios locales que no se trackean en git
DATA_DIR = "local_data"
PERSIST_DIR = os.path.join(DATA_DIR, "chroma_db")
EMBEDDING_CACHE_DIR = os.path.join(DATA_DIR, "embedding_cache")

# Parámetros de búsqueda simplificados para garantizar compatibilidad
RETRIEVER_SEARCH_KWARGS = {
    "k": 5  # Número de documentos a recuperar
}

def ingest(pdf_paths=None):
    """
    Ingiere uno o varios documentos PDF para construir la base de conocimientos.
    
    Args:
        pdf_paths: Puede ser una ruta a un archivo PDF específico, una lista de rutas, 
                  o None para procesar todos los PDFs en el directorio data/reglamento/
    
    Returns:
        str: Mensaje con el resultado de la ingestión
    """
    try:
        start_time = time.time()
        
        # Si no se especifican rutas, procesar todos los PDFs en el directorio reglamento
        if pdf_paths is None:
            pdf_paths = glob.glob("data/reglamento/*.pdf")
            if not pdf_paths:
                logger.error("No se encontraron archivos PDF en data/reglamento/")
                return "Error: No se encontraron archivos PDF para ingestar"
        
        # Si es una sola ruta, convertirla a lista
        if isinstance(pdf_paths, str):
            pdf_paths = [pdf_paths]
        
        # Verificar que los archivos existan
        for pdf_path in pdf_paths:
            if not os.path.exists(pdf_path):
                logger.error(f"El archivo {pdf_path} no existe")
                return f"Error: El archivo {pdf_path} no existe"
        
        # Asegurar que los directorios existan
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(EMBEDDING_CACHE_DIR, exist_ok=True)
        
        # Reiniciar la base de datos vectorial para asegurar una ingestión limpia
        if os.path.exists(PERSIST_DIR):
            logger.info(f"Eliminando base de datos vectorial existente: {PERSIST_DIR}")
            try:
                shutil.rmtree(PERSIST_DIR)
                logger.info("Base de datos vectorial eliminada correctamente")
            except Exception as e:
                logger.error(f"Error al eliminar base de datos: {str(e)}")
                # Continuar con la operación
                
        # Crear el directorio vacío
        os.makedirs(PERSIST_DIR, exist_ok=True)
        
        # Procesar cada PDF y recolectar todos los chunks
        all_chunks = []
        total_chunks = 0
        
        for pdf_path in pdf_paths:
            logger.info(f"Procesando documento: {pdf_path}")
            chunks = load_and_split_pdf(pdf_path)
            all_chunks.extend(chunks)
            total_chunks += len(chunks)
            logger.info(f"Documento {pdf_path} dividido en {len(chunks)} chunks")
        
        logger.info(f"Total de documentos procesados: {len(pdf_paths)}")
        logger.info(f"Total de chunks: {total_chunks}")
        
        # Configurar embeddings
        embedding = FastEmbedEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            cache_dir=EMBEDDING_CACHE_DIR
        )
        
        # Crear la base de vectores
        Chroma.from_documents(
            documents=all_chunks,
            embedding=embedding,
            persist_directory=PERSIST_DIR,
            collection_metadata={"hnsw:space": "cosine"}
        )
        
        # Limpiar caché para reflejar nueva base de conocimiento
        RESPONSE_CACHE.clear()
        
        elapsed_time = time.time() - start_time
        logger.info(f"Ingestión completada en {elapsed_time:.2f} segundos")
        
        return f"Ingestión completada en {elapsed_time:.2f} segundos. Se procesaron {total_chunks} fragmentos de {len(pdf_paths)} documentos."
    except Exception as e:
        logger.error(f"Error durante la ingestión: {str(e)}", exc_info=True)
        return f"Error durante la ingestión: {str(e)}"

def get_query_hash(query):
    """Genera un hash único para la consulta para usar como clave de caché"""
    return hashlib.md5(query.lower().strip().encode('utf-8')).hexdigest()

def ask(query: str):
    try:
        start_time = time.time()
        logger.info(f"Procesando consulta: {query}")
        
        # Verificar en caché
        query_hash = get_query_hash(query)
        if query_hash in RESPONSE_CACHE:
            logger.info(f"Respuesta encontrada en caché para: {query}")
            elapsed_time = time.time() - start_time
            logger.info(f"Consulta procesada desde caché en {elapsed_time:.2f} segundos")
            return RESPONSE_CACHE[query_hash]
        
        # Configurar embeddings y vectorstore
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(EMBEDDING_CACHE_DIR, exist_ok=True)
        
        embedding = FastEmbedEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            cache_dir=EMBEDDING_CACHE_DIR
        )
        
        # Verificar que el directorio de persistencia exista
        if not os.path.exists(PERSIST_DIR):
            logger.error(f"El directorio de persistencia {PERSIST_DIR} no existe.")
            return "Lo siento, ha ocurrido un error al cargar la base de conocimiento. Por favor, asegúrate de que se ha realizado la ingestión de documentos."
        
        vectorstore = Chroma(
            persist_directory=PERSIST_DIR, 
            embedding_function=embedding,
            collection_metadata={"hnsw:space": "cosine"}
        )
        
        # Analizamos la query para determinar el mejor retriever
        query_lower = query.lower()
        
        # Palabras clave que sugieren consulta sobre preguntas frecuentes
        faq_keywords = ["pregunta", "frecuente", "común", "duda", "consulta", "inquietud", 
                       "cómo", "como", "proceso", "trámite", "tramite", "inscripción", "inscripcion", 
                       "matrícula", "matricula", "admisión", "admision", "horario", "calendario", 
                       "servicio", "bienestar", "plazo", "fecha", "requisito", "paso", "procedimiento"]
        
        # Palabras clave que sugieren consulta sobre reglamento - AMPLIADAS
        reglamento_keywords = ["reglamento", "norma", "regla", "artículo", "articulo", "sanción", "sancion", 
                               "prohibición", "prohibicion", "obligación", "obligacion", "derecho", "deber", 
                               "estatuto", "código", "codigo", "disciplina", "académico", "academico", 
                               "calificación", "calificacion", "nota", "evaluación", "evaluacion", "examen",
                               "falta", "gravísima", "gravisima", "grave", "leve", "suspensión", "suspension",
                               "cancelación", "cancelacion", "matrícula", "matricula", "disciplinaria", "disciplinario",
                               "conducta", "comportamiento", "infracción", "infraccion", "penalidad", "castigo"]
        
        # Verificar si la consulta parece una pregunta de FAQ basada en su estructura
        is_question_structure = any(query_lower.startswith(prefix) for prefix in ["cómo", "como", "qué", "que", "cuál", "cual", "dónde", "donde", "cuándo", "cuando"])
        
        # Verificar si la consulta contiene palabras clave específicas
        is_faq_related = any(keyword in query_lower for keyword in faq_keywords) or is_question_structure
        is_reglamento_related = any(keyword in query_lower for keyword in reglamento_keywords)
        
        # Si la consulta contiene términos específicos que SIEMPRE deben dirigirse al reglamento
        critical_reglamento_terms = ["sanción", "sancion", "falta", "gravísima", "gravisima", "grave", 
                                    "disciplinaria", "suspensión", "suspension", "cancelación", "cancelacion"]
        is_critical_reglamento = any(term in query_lower for term in critical_reglamento_terms)
        
        search_kwargs = {"k": 5}
        # Estrategia de búsqueda
        if is_critical_reglamento:
            # Para términos críticos del reglamento, ignorar cualquier otra clasificación
            logger.info(f"Consulta clasificada como CRÍTICA DE REGLAMENTO: {query}")
            search_kwargs = {"k": 6, "filter": {"document_type": "reglamento_universitario"}}
            
        elif is_faq_related and not is_reglamento_related:
            # Priorizar preguntas frecuentes - Estrategia específica para FAQ
            logger.info(f"Consulta clasificada como FAQ: {query}")
            search_kwargs = {"k": 6, "filter": {"document_type": "preguntas_frecuentes"}}
            
        elif is_reglamento_related and not is_faq_related:
            # Priorizar reglamento
            logger.info(f"Consulta clasificada como reglamento: {query}")
            search_kwargs = {"k": 6, "filter": {"document_type": "reglamento_universitario"}}
            
        else:
            # Estrategia híbrida: Evaluar ambas fuentes
            logger.info(f"Consulta mixta o general: {query}")
            
            # Usar una estrategia basada en scores de similitud para determinar la mejor fuente
            try:
                # Obtener documentos de ambas fuentes para comparar relevancia
                faq_retriever = vectorstore.as_retriever(
                    search_kwargs={"k": 3, "filter": {"document_type": "preguntas_frecuentes"}}
                )
                reglamento_retriever = vectorstore.as_retriever(
                    search_kwargs={"k": 3, "filter": {"document_type": "reglamento_universitario"}}
                )
                
                # Verificar contenido de ambos documentos
                faq_docs = faq_retriever.get_relevant_documents(query)
                reglamento_docs = reglamento_retriever.get_relevant_documents(query)
                
                # Realizar evaluación de relevancia entre documentos
                use_faq = False
                
                # Si encontramos documentos en FAQ pero ninguno en reglamento
                if faq_docs and not reglamento_docs:
                    logger.info("Solo se encontraron documentos FAQ - usando FAQ")
                    use_faq = True
                
                # Si encontramos documentos en reglamento pero ninguno en FAQ
                elif reglamento_docs and not faq_docs:
                    logger.info("Solo se encontraron documentos de reglamento - usando reglamento")
                    use_faq = False
                
                # Si encontramos documentos en ambas fuentes, evaluar palabras clave en el contenido
                elif faq_docs and reglamento_docs:
                    # Buscar términos críticos en los contenidos recuperados
                    reglamento_content = " ".join([doc.page_content.lower() for doc in reglamento_docs])
                    
                    # Verificar si hay términos críticos en el contenido del reglamento
                    if any(term in reglamento_content for term in critical_reglamento_terms):
                        logger.info("Se encontraron términos críticos en el contenido del reglamento - priorizando reglamento")
                        use_faq = False
                    else:
                        # En caso de duda para consultas generales, preferir FAQ por ser más directas
                        logger.info("No se encontraron términos críticos - usando FAQ por defecto para consultas generales")
                        use_faq = True
                
                # Configurar retriever según la evaluación
                if use_faq:
                    search_kwargs = {"k": 6, "filter": {"document_type": "preguntas_frecuentes"}}
                    logger.info("Seleccionado: Documento de Preguntas Frecuentes")
                else:
                    search_kwargs = {"k": 6, "filter": {"document_type": "reglamento_universitario"}}
                    logger.info("Seleccionado: Reglamento Universitario")
                
            except Exception as e:
                logger.warning(f"Error en evaluación de fuentes: {str(e)}")
                # Si hay error, usar estrategia mixta con más documentos
                search_kwargs = {"k": 7}
        
        # Crear un retriever con los parámetros determinados
        retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
        
        # Prompt mejorado con instrucciones más precisas y énfasis en la fuente
        prompt = ChatPromptTemplate.from_template("""
        Eres Ardy, un asistente virtual especializado en información universitaria de la Universidad de Ibagué. 
        Responde de forma clara, concisa y amigable, basándote exclusivamente en la siguiente información:

        {context}

        Reglas importantes:
        1. Tus respuestas deben ser amigables y conversacionales, dirigidas a estudiantes universitarios.
        2. SIEMPRE debes mencionar específicamente la fuente de tu información, indicando si proviene del "Reglamento Universitario" o del documento de "Preguntas Frecuentes".
        3. Si la pregunta es sobre normas, sanciones, derechos, deberes o aspectos disciplinarios, asegúrate de usar la información del "Reglamento Universitario".
        4. Da preferencia a la información más específica y completa sobre el tema consultado.
        5. Si la información está parcialmente en el contexto, proporciona lo que encuentres e indica qué parte falta.
        6. Si la información no está en el contexto, indica claramente que no tienes esa información en los documentos disponibles.
        7. No inventes información ni interpretes más allá de lo que está explícitamente en el contexto.
        8. Proporciona respuestas directas y específicas a la pregunta del usuario.

        Pregunta del estudiante: {input}
        """)
        
        # Configuración del modelo con parámetros optimizados
        model = ChatOllama(
            model="llama3",
            temperature=0.1,  # Baja temperatura para respuestas más precisas
            num_predict=1024,  # Aumentado para permitir respuestas más completas
            stop=["Estudiante:", "Usuario:", "Human:"],  # Evitar que el modelo continúe la conversación
            repeat_penalty=1.2,  # Penalizar repeticiones
        )
        
        # Crear una cadena de documentos optimizada
        document_chain = create_stuff_documents_chain(
            llm=model,
            prompt=prompt,
            document_variable_name="context"
        )
        
        # Crear la cadena de recuperación
        retrieval_chain = create_retrieval_chain(
            retriever=retriever,
            combine_docs_chain=document_chain
        )
        
        # Invocar la cadena con el retriever adecuado
        response = retrieval_chain.invoke({"input": query})
        
        elapsed_time = time.time() - start_time
        logger.info(f"Consulta procesada en {elapsed_time:.2f} segundos")
        
        if "answer" in response:
            answer = response["answer"]
            
            # Guardar en caché
            if len(RESPONSE_CACHE) >= MAX_CACHE_SIZE:
                # Eliminar una entrada aleatoria si el caché está lleno
                RESPONSE_CACHE.pop(next(iter(RESPONSE_CACHE)))
            RESPONSE_CACHE[query_hash] = answer
            
            return answer
        else:
            logger.error(f"La respuesta no contiene el campo 'answer': {response}")
            return "Lo siento, ha ocurrido un error al generar la respuesta."
    except Exception as e:
        logger.error(f"Error al procesar la consulta: {str(e)}", exc_info=True)
        
        # Mensaje de error más descriptivo
        error_msg = str(e)
        if "Collection.query()" in error_msg and "unexpected keyword argument" in error_msg:
            return "Error en la configuración de búsqueda. Por favor, contacta al administrador del sistema para reingestar los documentos."
        elif "no such file or directory" in error_msg.lower():
            return "Error al acceder a la base de conocimiento. Por favor, utiliza el botón 'Reingestar Documentos' en el panel lateral."
        
        return "Lo siento, ha ocurrido un error. Por favor, intenta de nuevo o reinicia la aplicación."
