from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.agents.agent_factory import build_agent, list_agents


router = APIRouter(prefix="/agent", tags=["agent"])


class AgentQuery(BaseModel):
    input: str
    agent: Optional[str] = "default"
    extra_tools: Optional[list[str]] = None


@router.get("/list")
def list_available_agents() -> Dict[str, Any]:
    return {"agents": list_agents()}


@router.post("/query")
def run_agent(query: AgentQuery) -> Dict[str, Any]:
    executor = build_agent(query.agent or "default", extra_tools=query.extra_tools)
    result = executor.invoke({"input": query.input})
    # LangChain AgentExecutor returns a dict with 'output'
    output = result.get("output", result)
    return {"response": output}

