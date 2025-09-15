from langchain_core.tools import tool
from app.services import insight_services


@tool("initialize_insights")
def initialize_insights(file: str, force: bool = False) -> str:
    """
    Initialize or update the vector index for the specified uploaded file.

    Args:
        file: The filename under the uploads directory (e.g. mydoc.pdf).

    Returns:
        A status message string.
    """
    try:
        vs = insight_services.create_vector_store(file, force=force)
        if vs:
            return f"AI is initialized for file: {file} (force={force})"
        return f"No vector store created for file: {file}"
    except Exception as e:
        return f"Error initializing AI Assistant for file: {file}: {e}"
