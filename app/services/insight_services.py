from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from app.utils.Logging.logger import logger
import os
from app.core.config import settings    
from app.services.file_registry_services import get_file_by_name
from app.utils.fileops.fileutils import hash_file

# Expect OPENAI_API_KEY in env.
# If you're using Azure OpenAI, see the notes below.

def create_vector_store(file: str):
    try:        
        # logger.info(f"Creating vector store for file: {file} with hash: {hash_value}")
        file_location = os.path.join(settings.UPLOAD_DIR, file)
        # 1) Load PDF
        loader = PyPDFLoader(file_location)
        documents = loader.load()

        # 2) Split into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(documents)

        # 3) OpenAI embeddings (no torch)
        # text-embedding-3-small is cheap and solid; swap to -large for best quality.
        if settings.APP_ENV == "development":            
            from langchain_huggingface import HuggingFaceEmbeddings
            embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        else:   
            embedding = OpenAIEmbeddings(model="text-embedding-3-small")

        # 4) Create/persist Chroma DB
        #persist_dir = f"vector_store/{hash_value}" if hash_value else "vector_store/default"
        persist_dir = get_file_by_name(file)[3]
        if(not os.path.exists(persist_dir)):
            db = Chroma.from_documents(
                documents=chunks,
                embedding=embedding,
                persist_directory=persist_dir,
            )
            # Make sure it’s flushed to disk        
            db.persist()        
            logger.info(f"Vector store created at: {persist_dir}")
        else:            
            db = Chroma(persist_directory=persist_dir, embedding_function=embedding)
            logger.info(f"Using existing vector store at: {persist_dir}")

        return db
    except Exception as e:
        logger.error(f"Error creating vector store for file {file}: {e}")
        raise
