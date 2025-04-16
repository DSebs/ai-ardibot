# chatbot/utils.py

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

def load_and_split_pdf(pdf_path: str):
    loader = PyPDFLoader(pdf_path)
    pages = loader.load_and_split()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=100,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(pages)
    return chunks
