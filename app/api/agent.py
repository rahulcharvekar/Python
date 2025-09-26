from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import re

from app.agents.agent_factory import list_agents
from app.agent_processing import handle_agent_query, handle_agent_files
from app.services.generic import ingestion_db


router = APIRouter(prefix="/agent", tags=["agent"])


class AgentPathQuery(BaseModel):
    input: str
    extra_tools: Optional[list[str]] = None
    session_id: Optional[str] = None
    filename: Optional[str] = None


class ProfileChatRequest(BaseModel):
    filename: str
    query: str
    extra_tools: Optional[list[str]] = None
    session_id: Optional[str] = None
    k: Optional[int] = None
    score_threshold: Optional[float] = None
    strict: Optional[bool] = None

    class Config:
        extra = "ignore"


def _validate_text(text: str) -> Optional[str]:
    """Return error message if invalid, else None."""
    allowed = re.compile(r"^[A-Za-z0-9\s\-_/\.,:;@()<>\+\#&]*$")
    if re.search(r"<[^>]+>", text or ""):
        return "Please replace placeholders like <...> with actual values before sending."
    if not allowed.fullmatch(text or ""):
        return "Input contains disallowed special characters."
    return None


def _resolve_agent_name(name_or_slug: str) -> Optional[str]:
    """Map a path value to a configured agent name (case-insensitive)."""
    available = list(list_agents().keys())
    # Exact match first
    if name_or_slug in available:
        return name_or_slug
    lower_map = {k.lower(): k for k in available}
    return lower_map.get((name_or_slug or "").lower())

@router.get("/list")
def list_available_agents() -> Dict[str, Any]:
    return {"agents": list_agents()}


@router.post("/query/{agent}")
def run_agent_by_path(agent: str, query: AgentPathQuery) -> Dict[str, Any]:
    err = _validate_text(query.input)
    if err:
        return {"response": err}

    resolved = _resolve_agent_name(agent)
    if not resolved:
        raise HTTPException(status_code=404, detail="Unknown agent")

    return handle_agent_query(
        input_text=query.input,
        agent=resolved,
        extra_tools=query.extra_tools,
        session_id=query.session_id,
        filename=query.filename,
    )


@router.get("/listfiles/{agent}")
def list_agent_files(agent: str) -> Dict[str, Any]:
    resolved = _resolve_agent_name(agent)
    if not resolved:
        raise HTTPException(status_code=404, detail="Unknown agent")
    return handle_agent_files(agent=resolved)


@router.post("/profilechat/{agent}")
def chat_profile(agent: str, payload: ProfileChatRequest) -> Dict[str, Any]:
    resolved = _resolve_agent_name(agent)
    if not resolved:
        raise HTTPException(status_code=404, detail="Unknown agent")
    if resolved != "recruiter":
        raise HTTPException(status_code=400, detail="Profile chat is only supported for the recruiter agent")

    err = _validate_text(payload.query)
    if err:
        raise HTTPException(status_code=400, detail=err)

    if not (payload.query or "").strip():
        raise HTTPException(status_code=400, detail="query is required")

    filename = (payload.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")

    try:
        rows = ingestion_db.list_documents(resolved)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to load documents for {resolved}: {exc}")

    known_files = {r.get("file") for r in rows if isinstance(r, dict) and isinstance(r.get("file"), str)}
    if filename not in known_files:
        raise HTTPException(status_code=404, detail=f"File '{filename}' is not registered for agent '{resolved}'")

    # Reuse agent processing pipeline so prompt/tool orchestration is consistent
    result = handle_agent_query(
        input_text=payload.query,
        agent=resolved,
        extra_tools=payload.extra_tools,
        session_id=payload.session_id,
        filename=filename,
    )

    response_content = result.get("response")
    if isinstance(response_content, (dict, list)):
        response_text = json.dumps(response_content, ensure_ascii=False)
    else:
        response_text = str(response_content)

    return {
        "response": response_text,
        "session_id": result.get("session_id"),
        "files": result.get("files", []),
    }
