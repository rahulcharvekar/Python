from typing import Optional, Dict, Any, List
from .registry import get_handler
from .base import AgentContext
from app.services.generic import ingestion_db


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
    return {"response": result.response, "session_id": result.session_id}


def handle_agent_files(*, agent: Optional[str]) -> Dict[str, Any]:
    """Return a list of files known to the given agent.

    Output shape: {"files": [{"file": str, "title": str|None, "updated_at": Any}]}
    """
    name = agent or "DocHelp"
    allowed_by_agent = {
        "Recruiter": {".pdf", ".txt", ".md", ".docx", ".doc"},
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
            "file": f,
            "title": r.get("title") if isinstance(r, dict) else None,
            "updated_at": r.get("updated_at") if isinstance(r, dict) else None,
        })
    return {"files": files}
