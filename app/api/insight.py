# api/upload_file.py

from fastapi import APIRouter
from app.agents.agent_factory import build_agent

router = APIRouter(prefix="/get_insights", tags=["get_insights"])


@router.post("/{file}")
async def initialize_ai(file):
    # Route through the agent so tool selection remains flexible
    executor = build_agent("DocHelp")
    user_input = f"Initialize or update the vector index for file '{file}'."
    result = executor.invoke({"input": user_input})
    return {"response": result.get("output", result)}
