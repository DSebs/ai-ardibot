from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

from .utils import load_and_split_pdf

PERSIST_DIR = "sql_chroma_db"

def ingest(pdf_path: str = "data/reglamento.pdf"):
    chunks = load_and_split_pdf(pdf_path)
    embedding = FastEmbedEmbeddings()
    Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        persist_directory=PERSIST_DIR
    )

def build_chain():
    embedding = FastEmbedEmbeddings()
    vectorstore = Chroma(persist_directory=PERSIST_DIR, embedding_function=embedding)
    retriever = vectorstore.as_retriever()

    # Prompt como string plano
    prompt_template = """
    Responde de forma clara y basada en el siguiente contexto:

    {context}

    Pregunta: {input}
    """

    model = ChatOllama(model="llama3")

    def chain_fn(input_dict):
        docs = retriever.get_relevant_documents(input_dict["input"])
        context = "\n\n".join(doc.page_content for doc in docs)
        prompt = prompt_template.format(context=context, input=input_dict["input"])
        return model.invoke(prompt)

    return chain_fn

def ask(query: str):
    chain = build_chain()
    response = chain({"input": query})
    return response.content if hasattr(response, "content") else response
