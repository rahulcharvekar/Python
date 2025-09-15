from langchain_core.tools import tool
from app.services import agent_file_registry


@tool("list_agent_files")
def list_agent_files(agent: str) -> str:
    """
    List files registered for the specified agent only (JSON registry under uploads).
    Returns a JSON-like string: { files: [...] }.
    """
    try:
        files = agent_file_registry.list_for_agent(agent)
        return str({"files": files})
    except Exception as e:
        return str({"files": [], "error": str(e)})

