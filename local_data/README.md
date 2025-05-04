# Local Data Directory

Este directorio contiene datos que se generan localmente y no se incluyen en el control de versiones:

- `chroma_db/` - Base de datos vectorial de ChromaDB
- `embedding_cache/` - Caché de embeddings para FastEmbed

Estos archivos se generan automáticamente cuando se ejecuta la aplicación y no se deben incluir en los commits de Git debido a su gran tamaño.

**Nota:** Si eliminas este directorio, simplemente se regenerará la próxima vez que ejecutes la aplicación. 