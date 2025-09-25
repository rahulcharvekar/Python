from __future__ import annotations

from langchain_core.tools import tool
from typing import List, Dict, Any

from app.services.generic import chat_service
from app.services.agents import dochelp_service


@tool("chat_over_file")
def chat_over_file(file: str, query: str) -> str:
    """
    Answer a natural language question grounded in the given uploaded file.
    """
    result = chat_service.answer(
        file,
        query,
        k=24,
        score_threshold=0.0,
        strict=False,
    )
    if isinstance(result, dict) and "response" in result:
        return str(result["response"])  # type: ignore[index]
    return str(result)


@tool("list_indexed_docs_db")
def list_indexed_docs_db(agent: str = "DocHelp") -> str:
    """
    List DocHelp documents persisted in the generic ingestion DB.
    Returns { documents: [{file, title, vector_collection, updated_at}, ...] }.
    """
    try:
        rows = dochelp_service.list_indexed_docs(agent)
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "file": r.get("file"),
                    "title": r.get("title"),
                    "vector_collection": r.get("vector_collection"),
                    "updated_at": r.get("updated_at"),
                }
            )
        return str({"documents": out})
    except Exception as e:
        return str({"documents": [], "error": str(e)})
