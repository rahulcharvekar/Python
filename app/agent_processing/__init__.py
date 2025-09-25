from typing import Optional, Dict, Any, List
from .registry import get_handler
from .base import AgentContext
from app.services.generic import ingestion_db


def _summarize_query(text: Optional[str], max_length: int = 120) -> str:
    """Return a condensed single-line summary of the user query."""
    if not text:
        return "your request"
    summary = " ".join(text.split())
    if len(summary) > max_length:
        summary = summary[: max_length - 1].rstrip() + "…"
    return summary or "your request"


def handle_agent_query(
    *,
    input_text: str,
    agent: Optional[str] = None,
    extra_tools: Optional[list[str]] = None,
    session_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Entry point for processing an agent query. Selects the agent, builds context,
    delegates to the appropriate handler, and returns a response dict.
    """
    ctx = AgentContext(
        input_text=input_text,
        agent_name=agent,
        extra_tools=extra_tools,
        session_id=session_id,
        file_override=filename,
    )

    handler = get_handler(agent)
    result = handler.handle(ctx)

    files = result.files or []
    response_payload = result.response
    if files:
        response_payload = f"Please find the filtered files for your query: {_summarize_query(input_text)}"

    return {
        "response": response_payload,
        "session_id": result.session_id,
        "files": files,
    }


def handle_agent_files(*, agent: Optional[str]) -> Dict[str, Any]:
    """Return a list of files known to the given agent.

    Output shape: {"files": [{"file": str, "title": str|None, "updated_at": Any}]}
    """
    name = agent or "DocHelp"
    allowed_by_agent = {
        "DocHelp": {".pdf", ".csv", ".txt", ".md", ".docx", ".doc"},
    }
    allowed = allowed_by_agent.get(name, {".pdf", ".csv", ".txt", ".md", ".docx", ".doc"})
    try:
        rows = ingestion_db.list_documents(name)
    except Exception:
        rows = []
    files: List[Dict[str, Any]] = []
    import os
    for r in rows:
        f = r.get("file") if isinstance(r, dict) else None
        if not isinstance(f, str):
            continue
        _, ext = os.path.splitext(f)
        if ext.lower() not in allowed:
            continue
        files.append({
            "agent": r.get("agent") if isinstance(r, dict) else None,
            "file": f,
            "title": r.get("title") if isinstance(r, dict) else None,
            "vector_collection": r.get("vector_collection") if isinstance(r, dict) else None,
            "keywords": r.get("keywords") if isinstance(r, dict) else None,
            "created_at": r.get("created_at") if isinstance(r, dict) else None,
            "updated_at": r.get("updated_at") if isinstance(r, dict) else None,
        })
    return {"files": files}
