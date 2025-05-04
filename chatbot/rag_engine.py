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

PERSIST_DIR = "chroma_db_v2"
RETRIEVER_SEARCH_KWARGS = {
    "k": 4  # número de documentos a recuperar
}

def ingest(pdf_path: str = "data/reglamento/reglamento-universitario.pdf"):
    try:
        logger.info(f"Iniciando ingestión del documento: {pdf_path}")
        start_time = time.time()
        
        # Verificar que el archivo exista
        if not os.path.exists(pdf_path):
            logger.error(f"El archivo {pdf_path} no existe")
            return f"Error: El archivo {pdf_path} no existe"
        
        chunks = load_and_split_pdf(pdf_path)
        logger.info(f"Documentos divididos: {len(chunks)} chunks")
        
        embedding = FastEmbedEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            cache_dir="./embedding_cache"
        )
        
        # Asegurar que el directorio de persistencia exista
        os.makedirs(PERSIST_DIR, exist_ok=True)
        
        Chroma.from_documents(
            documents=chunks,
            embedding=embedding,
            persist_directory=PERSIST_DIR
        )
        
        # Limpiar caché para reflejar nueva base de conocimiento
        RESPONSE_CACHE.clear()
        
        elapsed_time = time.time() - start_time
        logger.info(f"Ingestión completada en {elapsed_time:.2f} segundos")
        return f"Ingestión completada en {elapsed_time:.2f} segundos. Se procesaron {len(chunks)} fragmentos."
    except Exception as e:
        logger.error(f"Error durante la ingestión: {str(e)}", exc_info=True)
        return f"Error durante la ingestión: {str(e)}"

def build_chain():
    try:
        # Asegurar que el directorio de embeddings exista
        os.makedirs("./embedding_cache", exist_ok=True)
        
        embedding = FastEmbedEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            cache_dir="./embedding_cache"
        )
        
        # Verificar que el directorio de persistencia exista
        if not os.path.exists(PERSIST_DIR):
            logger.error(f"El directorio de persistencia {PERSIST_DIR} no existe, se creará uno nuevo.")
            os.makedirs(PERSIST_DIR, exist_ok=True)
            return None
        
        vectorstore = Chroma(persist_directory=PERSIST_DIR, embedding_function=embedding)
        retriever = vectorstore.as_retriever(search_kwargs=RETRIEVER_SEARCH_KWARGS)

        # Prompt mejorado con instrucciones específicas
        prompt = ChatPromptTemplate.from_template("""
        Eres un asistente especializado en el reglamento universitario. 
        Responde de forma clara, concisa y basada únicamente en el siguiente contexto:

        {context}

        Si la información no está en el contexto, indica que no tienes esa información 
        en el reglamento y sugiere al usuario que consulte directamente con la administración.
        No inventes información.

        Pregunta: {input}
        """)

        # Configuración del modelo con parámetros para mejorar la velocidad
        model = ChatOllama(
            model="llama3",
            temperature=0.1,
            num_predict=512,
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

        return retrieval_chain
    except Exception as e:
        logger.error(f"Error al construir la cadena: {str(e)}", exc_info=True)
        return None

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
        
        chain = build_chain()
        if chain is None:
            return "Lo siento, ha ocurrido un error al cargar la base de conocimiento. Por favor, asegúrate de que se ha realizado la ingestión de documentos."
        
        # Optimizar para ejecutar más rápido
        response = chain.invoke({"input": query})
        
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
        return f"Lo siento, ha ocurrido un error: {str(e)}. Por favor, intenta de nuevo más tarde."
