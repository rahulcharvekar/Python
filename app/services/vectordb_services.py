from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

def create_vector_store(file_path, hash_value=None):
    # Load the PDF file
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    # Split the documents into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)
    
    # Create embeddings
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Create a vector store
    db = Chroma.from_documents(
        chunks,
        embedding,
        persist_directory=f"vector_store/{hash_value}"
                )
    
    return db