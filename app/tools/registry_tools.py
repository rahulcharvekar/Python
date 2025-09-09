from langchain_core.tools import tool
from app.services import file_registry_services as file_registry


@tool("list_files")
def list_files() -> str:
    """
    List all files known in the registry.

    Returns:
        A JSON-like string listing files. Useful for the agent to inspect context.
    """
    rows = file_registry.get_all_files()
    return str({"files": rows or []})

