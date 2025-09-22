from __future__ import annotations

from langchain_core.tools import tool
from typing import List, Dict, Any

from app.services.agents import recruiter_service


@tool("enrich_resume")
def enrich_resume(file: str, agent: str = "Recruiter") -> str:
    """
    Enrich a resume's metadata for the Recruiter workflow (no vector creation).

    - Parses the resume text to extract fields (name, skills, experience, emails/phones) and keywords.
    - Upserts these fields into the SQLite ingestion DB for the given agent/file.
    - Reads the vector_collection that was created during upload and stores it alongside.

    This does not create or modify the vector embeddings; retrieval continues to use
    the same collection built at upload time for the full file. Use this to power
    deterministic filters and better UI displays.
    """
    try:
        info = recruiter_service.enrich_resume(file, agent=agent)
        return (
            f"Enriched '{info.get('file')}' via {info.get('loader')}; collection={info.get('collection')}; "
            f"skills={','.join(info.get('skills') or []) if info.get('skills') else '-'}"
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
        { file, name, vector_collection, skills, updated_at }.
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
                    "skills": r.get("skills"),
                    "keywords": r.get("keywords"),
                    "updated_at": r.get("updated_at"),
                }
            )
        return str({"profiles": out})
    except Exception as e:
        return str({"profiles": [], "error": str(e)})
