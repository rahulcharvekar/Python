from langchain_core.tools import tool
from app.core.config import settings
import os


@tool("list_files")
def list_files() -> str:
    """
    List uploaded files directly from the uploads directory (no SQL dependency).

    Returns:
        A JSON-like string listing filenames.
    """
    try:
        up = settings.UPLOAD_DIR
        if not os.path.isdir(up):
            return str({"files": []})
        allowed = {".pdf", ".csv", ".txt", ".md"}
        files = [f for f in os.listdir(up) if os.path.isfile(os.path.join(up, f))]
        names = [f for f in files if os.path.splitext(f)[1].lower() in allowed]
        return str({"files": names})
    except Exception as e:
        return str({"files": [], "error": str(e)})
