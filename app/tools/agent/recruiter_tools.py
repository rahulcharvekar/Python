from __future__ import annotations

from langchain_core.tools import tool
from typing import List, Dict, Any

from app.services.agents import recruiter_service
from app.services.generic import chat_service


@tool("enrich_resume")
def enrich_resume(file: str, agent: str = "Recruiter") -> str:
    """
    Register/update the resume row for the Recruiter workflow (no vector creation).

    Persists/refreshes the document entry in the ingestion DB and associates it
    with the existing vector collection created during upload.
    """
    try:
        info = recruiter_service.enrich_resume(file, agent=agent)
        return (
            f"Enriched '{info.get('file')}' via {info.get('loader')}; collection={info.get('collection')}"
        )
    except Exception as e:
        return f"Failed to enrich '{file}': {e}"


@tool("list_indexed_profiles_db")
def list_indexed_profiles_db(agent: str = "Recruiter") -> str:
    """
    List resumes ingested for the given agent from the generic ingestion DB.

    Args:
        agent: Agent name to filter rows by (default: "Recruiter").

    Returns:
        A JSON-like string with key "profiles" containing an array of objects
        { file, name, vector_collection, updated_at }.
    """
    try:
        rows = recruiter_service.list_indexed_profiles(agent)
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "file": r.get("file"),
                    "name": r.get("name"),
                    "vector_collection": r.get("vector_collection"),
                    "updated_at": r.get("updated_at"),
                }
            )
        return str({"profiles": out})
    except Exception as e:
        return str({"profiles": [], "error": str(e)})

@tool("chat_over_profile")
def chat_over_profile(file: str, query: str) -> str:
    """
    Answer a question grounded in the profile file with strict, file-only retrieval.
    """
    result = chat_service.answer(
        file,
        query,
        k=12,
        score_threshold=0.45,
        strict=True,
    )
    if isinstance(result, dict) and "response" in result:
        return str(result["response"])  # type: ignore[index]
    return str(result)