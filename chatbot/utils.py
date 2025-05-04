# chatbot/utils.py

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import hashlib
import pickle

# Directorio para el cache
CACHE_DIR = "./document_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def load_and_split_pdf(pdf_path: str):
    # Verificar si existe caché del documento
    pdf_hash = hashlib.md5(open(pdf_path, "rb").read()).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{pdf_hash}.pkl")
    
    # Si existe caché, cargarlo directamente
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return pickle.load(f)
    
    # Si no existe caché, procesar el documento
    loader = PyPDFLoader(pdf_path)
    pages = loader.load_and_split()

    # Optimización: parámetros mejorados para la división de texto
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,  # Chunks más pequeños para mejor precisión
        chunk_overlap=200,  # Mayor superposición para mantener contexto
        length_function=len,
        add_start_index=True,
        separators=["\n\n", "\n", " ", ""],  # Separadores personalizados para mejor división
    )
    chunks = text_splitter.split_documents(pages)
    
    # Guardar en caché para futuras ejecuciones
    with open(cache_path, "wb") as f:
        pickle.dump(chunks, f)
    
    return chunks
