import os
from chatbot.rag_engine import ingest, ask

# Ruta al PDF
pdf_path = os.path.join("data", "reglamento", "reglamento-universitario.pdf")

# Verificamos que el PDF exista
assert os.path.exists(pdf_path), f"❌ El archivo no existe en la ruta: {pdf_path}"

# Ingesta del PDF
print("⏳ Iniciando ingesta del documento...")
ingest(pdf_path)
print("✅ Documento procesado y almacenado.")

# Realizar pregunta
query = "¿Cuáles son los tipos de categorías de los estudiantes de la Universidad de Ibagué?"
print(f"🧠 Pregunta: {query}")
answer = ask(query)

# Imprimir la respuesta del chatbot
print("🗨️ Respuesta del chatbot:")
print(answer if isinstance(answer, str) else str(answer))
