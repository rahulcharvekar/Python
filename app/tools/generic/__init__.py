"""Generic tool implementations shared across agents."""

from __future__ import annotations

from typing import List
import re

from langchain_core.tools import tool

from app.services.generic import chat_service
from app.services.generic import insight_services
from app.services.generic import ingestion_db


# chat_over_file is agent-facing (DocHelp); implemented in app/tools/agent/dochelp_tools.py


# --- Vector index management ---
@tool("initialize_insights")
def initialize_insights(file: str, force: bool = False) -> str:
    """Initialize or refresh the vector index for an uploaded file."""

    try:
        vs = insight_services.create_vector_store(file, force=force)
        if vs:
            return f"AI is initialized for file: {file} (force={force})"
        return f"No vector store created for file: {file}"
    except Exception as e:
        return f"Error initializing AI Assistant for file: {file}: {e}"


@tool("check_file_ready")
def check_file_ready(file: str) -> str:
    """Report whether an uploaded file has an indexed vector store ready for chat."""

    try:
        status = insight_services.check_vector_ready(file)
        return str(status)
    except Exception as e:
        return str({"file": file, "ready": False, "error": str(e)})


# --- Agent file registry utility ---
@tool("list_agent_files")
def list_agent_files(agent: str) -> str:
    """List files registered for the specified agent."""

    try:
        rows = ingestion_db.list_documents(agent)
        files: List[str] = []
        for r in rows:
            fn = r.get("file") if isinstance(r, dict) else None
            if isinstance(fn, str):
                files.append(fn)
        uniq = sorted(list(dict.fromkeys(files)))
        return str({"files": uniq})
    except Exception as e:
        return str({"files": [], "error": str(e)})


__all__ = [
    "initialize_insights",
    "check_file_ready",
    "list_agent_files",
]
