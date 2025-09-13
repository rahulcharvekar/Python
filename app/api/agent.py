from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.agents.agent_factory import list_agents
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
    return handle_agent_query(
        input_text=query.input,
        agent=query.agent,
        extra_tools=query.extra_tools,
        session_id=query.session_id,
    )
