from langchain_community.document_loaders import PyPDFLoader, CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from app.utils.Logging.logger import logger
import os
from pathlib import Path
from app.core.config import settings    
from app.services.file_registry_services import get_file_by_name
from app.utils.fileops.fileutils import hash_file

# Expect OPENAI_API_KEY in env.
# If you're using Azure OpenAI, see the notes below.

def create_vector_store(file: str):
    try:        
        # logger.info(f"Creating vector store for file: {file} with hash: {hash_value}")
        file_location = os.path.join(settings.UPLOAD_DIR, file)
        # Create a stable, content-based collection name using file hash
        file_hash = hash_file(file_location)
        # 1) Load PDF
        if file.endswith('.csv'):
            loader = CSVLoader(file_location)
        elif file.endswith('.pdf'):
            loader = PyPDFLoader(file_location)
        else:
            raise ValueError(f"Unsupported file type: {file}")
        documents = loader.load()

        # 2) Split into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(documents)

        # 3) OpenAI embeddings (no torch)
        # text-embedding-3-small is cheap and solid; swap to -large for best quality.
        if settings.APP_ENV == "development":            
            from langchain_huggingface import HuggingFaceEmbeddings
            embedding = HuggingFaceEmbeddings(model_name=settings.HUGGINGFACE_EMBEDDING_MODEL)
        else:   
            embedding = OpenAIEmbeddings(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_EMBEDDING_MODEL,
            )

        # 4) Create/persist Chroma DB
        persist_dir = Path(settings.CHROMA_DIR)
        # Use a unique, content-based collection name to avoid duplicates
        stem = Path(file).stem
        CHROMA_COLLECTION = f"{stem}-{file_hash[:12]}"
        logger.info(f"Using Chroma collection: {CHROMA_COLLECTION}")

        # Load existing collection (if any)
        vs = Chroma(
            collection_name=CHROMA_COLLECTION,
            persist_directory=persist_dir,
            embedding_function=embedding,
        )
        try:
            existing = vs._collection.count()  # type: ignore[attr-defined]
        except Exception:
            existing = 0

        if existing and existing > 0:
            logger.info(f"Collection already exists with {existing} docs; skipping re-ingestion")
            return vs

        # Fresh ingestion
        vs.add_documents(chunks)
        logger.info(f"Vector store created/updated at: {persist_dir}")
        return vs
    except Exception as e:
        logger.error(f"Error creating vector store for file {file}: {e}")
        raise
