from langchain_community.document_loaders import PyPDFLoader, CSVLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from app.utils.Logging.logger import logger
import os
from pathlib import Path
from app.core.config import settings    
from app.utils.fileops.fileutils import hash_file

# Expect OPENAI_API_KEY in env.
# If you're using Azure OpenAI, see the notes below.

def _resolve_path(file: str) -> str:
    """Resolve file path with priority: absolute → BASE_DIR → UPLOAD_DIR."""
    p = Path(file)
    if p.is_absolute() and os.path.exists(p):
        return str(p)
    base_candidate = Path(settings.BASE_DIR) / file
    if os.path.exists(base_candidate):
        return str(base_candidate)
    return str(Path(settings.UPLOAD_DIR) / file)


def create_vector_store(file: str):
    try:        
        # logger.info(f"Creating vector store for file: {file} with hash: {hash_value}")
        # Resolve path: absolute → BASE_DIR → UPLOAD_DIR
        file_location = _resolve_path(file)
        # Create a stable, content-based collection name using file hash
        file_hash = hash_file(file_location)
        # 1) Load PDF
        if file.endswith('.csv'):
            loader = CSVLoader(file_location)
        elif file.endswith('.pdf'):
            loader = PyPDFLoader(file_location)
        elif file.endswith('.txt') or file.endswith('.md'):
            # UTF-8 text/Markdown loader; preserves text cleanly vs PDF extraction
            loader = TextLoader(file_location, encoding='utf-8')
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


def check_vector_ready(file: str) -> dict:
    """
    Check whether the vector store for the given file exists and has embeddings.

    Returns a dict with keys: file, file_exists, collection, vector_count, ready.
    """
    try:
        # Resolve path: absolute → BASE_DIR → UPLOAD_DIR
        file_location = _resolve_path(file)
        exists = os.path.exists(file_location)
        if not exists:
            return {
                "file": file,
                "file_exists": False,
                "collection": None,
                "vector_count": 0,
                "ready": False,
            }

        file_hash = hash_file(file_location)
        stem = Path(file).stem
        CHROMA_COLLECTION = f"{stem}-{file_hash[:12]}"

        # Prepare embedding function (consistent with ingestion)
        if settings.APP_ENV == "development":
            from langchain_huggingface import HuggingFaceEmbeddings
            embedding = HuggingFaceEmbeddings(model_name=settings.HUGGINGFACE_EMBEDDING_MODEL)
        else:
            embedding = OpenAIEmbeddings(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_EMBEDDING_MODEL,
            )

        vs = Chroma(
            collection_name=CHROMA_COLLECTION,
            persist_directory=Path(settings.CHROMA_DIR),
            embedding_function=embedding,
        )
        try:
            count = int(vs._collection.count())  # type: ignore[attr-defined]
        except Exception:
            count = 0

        return {
            "file": file,
            "file_exists": True,
            "collection": CHROMA_COLLECTION,
            "vector_count": count,
            "ready": bool(count and count > 0),
        }
    except Exception as e:
        logger.error(f"Error checking vector readiness for file {file}: {e}")
        return {
            "file": file,
            "file_exists": False,
            "collection": None,
            "vector_count": 0,
            "ready": False,
            "error": str(e),
        }
