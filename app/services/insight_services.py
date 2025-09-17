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


def create_vector_store(file: str, force: bool = False):
    try:
        # Resolve path: absolute → BASE_DIR → UPLOAD_DIR
        file_location = _resolve_path(file)
        # Stable, content-based collection name using file hash
        file_hash = hash_file(file_location)

        # Prepare embedding function (lazy network usage happens only on add_documents)
        if settings.APP_ENV == "development":
            from langchain_huggingface import HuggingFaceEmbeddings
            embedding = HuggingFaceEmbeddings(model_name=settings.HUGGINGFACE_EMBEDDING_MODEL)
            logger.info(f"Embeddings backend | provider=huggingface | model={settings.HUGGINGFACE_EMBEDDING_MODEL} | file={file}")
        else:
            embedding = OpenAIEmbeddings(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_EMBEDDING_MODEL,
            )
            logger.info(f"Embeddings backend | provider=openai | model={settings.OPENAI_EMBEDDING_MODEL} | file={file}")

        # Create/load Chroma collection
        persist_dir = Path(settings.VECTOR_STORE_DIR)
        stem = Path(file).stem
        VECTOR_COLLECTION = f"{stem}-{file_hash[:12]}"
        logger.info(f"Using Chroma collection for file {file}: {VECTOR_COLLECTION}")
        vs = Chroma(
            collection_name=VECTOR_COLLECTION,
            persist_directory=persist_dir,
            embedding_function=embedding,
        )
        try:
            existing = int(vs._collection.count())  # type: ignore[attr-defined]
        except Exception:
            existing = 0

        # Optionally force a rebuild by deleting the existing collection
        if force and existing and existing > 0:
            try:
                # Best-effort drop using underlying client
                if hasattr(vs, "_client"):
                    vs._client.delete_collection(VECTOR_COLLECTION)  # type: ignore[attr-defined]
                    logger.info(f"Deleted existing collection for rebuild: {VECTOR_COLLECTION}")
                # Recreate a fresh handle after deletion
                vs = Chroma(
                    collection_name=VECTOR_COLLECTION,
                    persist_directory=persist_dir,
                    embedding_function=embedding,
                )
                existing = 0
            except Exception as e:
                logger.warning(f"Force rebuild requested but deletion failed; proceeding to add docs fresh: {e}")

        if existing and existing > 0:
            logger.info(f"Collection already exists with {existing} docs; skipping re-ingestion | file={file} | collection={VECTOR_COLLECTION}")
            return vs

        # Fresh ingestion only if empty: load, split, embed
        if file.endswith('.csv'):
            loader = CSVLoader(file_location)
        elif file.endswith('.pdf'):
            loader = PyPDFLoader(file_location)
        elif file.endswith('.txt') or file.endswith('.md'):
            loader = TextLoader(file_location, encoding='utf-8')
        else:
            raise ValueError(f"Unsupported file type: {file}")
        documents = loader.load()

        # Tune chunking per type: larger chunks for markdown and PDFs to keep structure/table rows together
        if file.endswith('.md'):
            splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
        elif file.endswith('.pdf'):
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        else:
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(documents)
        vs.add_documents(chunks)
        logger.info(f"Vector store created/updated | file={file} | collection={VECTOR_COLLECTION} | dir={persist_dir} | chunks={len(chunks)}")
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
        VECTOR_COLLECTION = f"{stem}-{file_hash[:12]}"

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
            collection_name=VECTOR_COLLECTION,
            persist_directory=Path(settings.VECTOR_STORE_DIR),
            embedding_function=embedding,
        )
        try:
            count = int(vs._collection.count())  # type: ignore[attr-defined]
        except Exception:
            count = 0

        return {
            "file": file,
            "file_exists": True,
            "collection": VECTOR_COLLECTION,
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
