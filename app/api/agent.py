from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.agents.agent_factory import build_agent, list_agents
from app.agents.session_memory import SessionMemory
from app.services import file_registry_services as file_registry
from app.services.intent_service import detect_file_intent


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
    # 1) Guardrail: local intent check to avoid LLM calls when not file-related
    try:
        known_rows = file_registry.get_all_files() or []
        known_filenames = [row.get("file_name") for row in known_rows if isinstance(row, dict)]
    except Exception:
        known_filenames = []

    intent = detect_file_intent(query.input, [f for f in known_filenames if f])

    # If not file intent, short-circuit with guidance (no OpenAI usage)
    if not intent.get("is_file_intent"):
        msg = "This assistant answers questions grounded in uploaded files. " \
              "Please upload a file and ask your question about it."
        if known_filenames:
            msg += f" Known files: {', '.join(known_filenames[:10])}"  # show a few
        if query.session_id:
            SessionMemory.append_user(query.session_id, query.input)
            SessionMemory.append_ai(query.session_id, msg)
        return {"response": msg, "session_id": query.session_id}

    # If file intent but no filename resolved and we have options, prompt user without LLM
    if not intent.get("matched_file") and known_filenames:
        msg = "Which file should I use? Available: " + ", ".join(known_filenames[:10])
        if query.session_id:
            SessionMemory.append_user(query.session_id, query.input)
            SessionMemory.append_ai(query.session_id, msg)
        return {"response": msg, "session_id": query.session_id}

    # 2) Proceed with agent when file-related (let agent call initialize_insights + chat_over_file)
    executor = build_agent(query.agent or "default", extra_tools=query.extra_tools)

    chat_history: List = []
    if query.session_id:
        # Append the new user turn and fetch full history
        SessionMemory.append_user(query.session_id, query.input)
        chat_history = SessionMemory.get(query.session_id)

    result = executor.invoke({
        "input": query.input,
        "chat_history": chat_history,
    })

    # LangChain AgentExecutor returns a dict with 'output'
    output = result.get("output", result)

    if query.session_id and isinstance(output, str):
        SessionMemory.append_ai(query.session_id, output)

    return {"response": output, "session_id": query.session_id}
