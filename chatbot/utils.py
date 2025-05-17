from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import hashlib
import pickle
import logging
from datetime import datetime
import re

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directorio para el cache
CACHE_DIR = "./document_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def load_and_split_pdf(pdf_path: str):
    """
    Carga un documento PDF y lo divide en chunks más pequeños para procesamiento.
    Usa caché para evitar reprocesar documentos ya procesados.
    
    Args:
        pdf_path: Ruta al archivo PDF a procesar
        
    Returns:
        List: Lista de documentos divididos
    """
    try:
        # Obtener información del archivo
        file_name = os.path.basename(pdf_path)
        file_size = os.path.getsize(pdf_path)
        file_modified = os.path.getmtime(pdf_path)
        modified_date = datetime.fromtimestamp(file_modified).strftime('%Y%m%d%H%M%S')
        
        # Crear un hash que incluya el nombre del archivo, tamaño y fecha de modificación
        pdf_hash = hashlib.md5(f"{file_name}_{file_size}_{modified_date}".encode()).hexdigest()
        cache_path = os.path.join(CACHE_DIR, f"{pdf_hash}.pkl")
        
        # Si existe caché y es actual, cargarlo directamente
        if os.path.exists(cache_path):
            logger.info(f"Usando caché para {file_name}")
            with open(cache_path, "rb") as f:
                return pickle.load(f)
        
        logger.info(f"Procesando documento: {file_name}")
        # Si no existe caché, procesar el documento
        loader = PyPDFLoader(pdf_path)
        pages = loader.load_and_split()

        # Identificar el tipo de documento basado en el nombre del archivo
        document_type = "otro_documento"
        document_title = "Documento Universitario"
        if 'reglamento' in file_name.lower():
            document_type = "reglamento_universitario"
            document_title = "Reglamento Universitario"
        elif 'pregunta' in file_name.lower() or 'faq' in file_name.lower() or 'frecuente' in file_name.lower():
            document_type = "preguntas_frecuentes"
            document_title = "Preguntas Frecuentes - ArdyBot"

        # Parámetros optimizados para la división de texto
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,           # Chunks más pequeños para mejor precisión
            chunk_overlap=150,        # Mayor solapamiento para mantener contexto
            length_function=len,
            add_start_index=True,
            separators=["\n\n", "\n", ". ", " ", ""],  # Separadores mejorados para mejor división
        )
        
        # Realizar la división de documentos
        chunks = text_splitter.split_documents(pages)
        
        # Añadir información rica sobre la fuente a los metadatos
        for i, chunk in enumerate(chunks):
            if 'source' in chunk.metadata:
                # Información básica del archivo
                chunk.metadata['filename'] = os.path.basename(chunk.metadata['source'])
                chunk.metadata['document_type'] = document_type
                chunk.metadata['document_title'] = document_title
                
                # Detectar posibles encabezados o títulos de sección
                content = chunk.page_content
                
                # Identificar posibles títulos o encabezados
                lines = content.strip().split('\n')
                if lines and len(lines[0]) < 100:  # Si la primera línea es corta, podría ser un título
                    chunk.metadata['possible_heading'] = lines[0]
                
                # Detectar si es una pregunta en documentos de FAQ
                if document_type == "preguntas_frecuentes":
                    # Patrones comunes de preguntas
                    question_patterns = [
                        r'^(?:¿|)[A-ZÁÉÍÓÚÑ][^?]*\?',  # Preguntas que empiezan con mayúscula y terminan con ?
                        r'(?:¿|)(?:Cómo|Qué|Dónde|Cuándo|Quién|Cuál|Por qué)[^?]*\?',  # Preguntas con palabras interrogativas
                    ]
                    
                    # Buscar patrones de preguntas en el contenido
                    for pattern in question_patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            chunk.metadata['contains_question'] = True
                            chunk.metadata['question_text'] = matches[0]
                            break
                
                # Agregar información de posición
                chunk.metadata['chunk_index'] = i
                
        # Guardar en caché para futuras ejecuciones
        with open(cache_path, "wb") as f:
            pickle.dump(chunks, f)
        
        logger.info(f"Documento {file_name} dividido en {len(chunks)} chunks")
        return chunks
        
    except Exception as e:
        logger.error(f"Error al procesar {pdf_path}: {str(e)}", exc_info=True)
        return []
