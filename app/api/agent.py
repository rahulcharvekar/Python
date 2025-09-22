from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import re

from app.agents.agent_factory import list_agents
from app.services.generic import ingestion_db
from app.agent_processing import handle_agent_query


router = APIRouter(prefix="/agent", tags=["agent"])


class AgentQuery(BaseModel):
    input: str
    agent: Optional[str] = "default"
    extra_tools: Optional[list[str]] = None
    session_id: Optional[str] = None


@router.get("/list")
def list_available_agents() -> Dict[str, Any]:
    return {"agents": list_agents()}


@router.post("/query")
def run_agent(query: AgentQuery) -> Dict[str, Any]:
    # Basic input validation: allow alphanumerics, whitespace, and a safe set of punctuation
    # Keeps slash commands and common tech terms like C++/C# permissible
    allowed = re.compile(r"^[A-Za-z0-9\s\-_/\.,:;@()<>\+\#&]*$")
    text = query.input or ""
    # Reject placeholder text like <...> so users must replace it before sending
    if re.search(r"<[^>]+>", text):
        return {"response": "Please replace placeholders like <...> with actual values before sending."}
    if not allowed.fullmatch(text):
        return {"response": "Input contains disallowed special characters."}
    return handle_agent_query(
        input_text=query.input,
        agent=query.agent,
        extra_tools=query.extra_tools,
        session_id=query.session_id,
    )
