from langchain_core.tools import tool
from app.services import insight_services


@tool("reindex_file")
def reindex_file(file: str) -> str:
    """
    Force-rebuild the vector index for a file (drops the existing collection).
    """
    try:
        insight_services.create_vector_store(file, force=True)
        return f"Re-indexed: {file}"
    except Exception as e:
        return f"Failed to re-index {file}: {e}"

