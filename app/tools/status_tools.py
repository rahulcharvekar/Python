from langchain_core.tools import tool
from app.services import insight_services


@tool("check_file_ready")
def check_file_ready(file: str) -> str:
    """
    Check whether the specified file has been vectorized and is ready for chat_over_file.

    Args:
        file: The filename under the uploads directory (e.g. mydoc.pdf).

    Returns:
        A JSON-like string with keys: file, file_exists, collection, vector_count, ready.
    """
    try:
        status = insight_services.check_vector_ready(file)
        return str(status)
    except Exception as e:
        return str({"file": file, "ready": False, "error": str(e)})

