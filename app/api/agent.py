from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

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


@router.get("/listfiles")
def list_agent_files(agent: str) -> Dict[str, Any]:
    """
    List all documents known for the specified agent from SQLite (ingestion_db).
    Exposes all fields returned by ingestion_db.list_documents for each item.
    """
    try:
        rows = ingestion_db.list_documents(agent)
        return {
            "agent": agent,
            "count": len(rows),
            "items": rows,
        }
    except Exception as e:
        return {"agent": agent, "count": 0, "items": [], "error": str(e)}


@router.post("/query")
def run_agent(query: AgentQuery) -> Dict[str, Any]:
    return handle_agent_query(
        input_text=query.input,
        agent=query.agent,
        extra_tools=query.extra_tools,
        session_id=query.session_id,
    )
