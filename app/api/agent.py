from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.agents.agent_factory import build_agent, list_agents, select_agent_name
from app.agents.session_memory import SessionMemory
from app.services import file_registry_services as file_registry
from app.services.intent_service import detect_file_intent
from app.core.config import settings


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
    # Determine agent first
    agent_name = query.agent or select_agent_name(query.input)

    # If MyProfile is selected but not configured, guide the user
    if agent_name == "MyProfile" and not settings.MYPROFILE_FILE:
        msg = "MyProfile is not configured. Set MYPROFILE_FILE to an absolute path (e.g., /PYTHON/app/profile.md) or place the file under uploads."
        if query.session_id:
            SessionMemory.append_user(query.session_id, query.input)
            SessionMemory.append_ai(query.session_id, msg)
        return {"response": msg, "session_id": query.session_id}

    # 1) Guardrail: local intent check to avoid LLM calls when not file-related
    #    Skip for MyProfile so it can handle general profile prompts.
    if agent_name != "MyProfile":
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

        # If a filename was mentioned but it doesn't exist in the registry, block with guidance
        mentioned = intent.get("matched_file")
        if mentioned:
            norm_known = {str(f).lower(): f for f in known_filenames if f}
            if mentioned.lower() not in norm_known:
                msg = f"File '{mentioned}' not found. "
                if known_filenames:
                    msg += "Available: " + ", ".join(known_filenames[:10])
                if query.session_id:
                    SessionMemory.append_user(query.session_id, query.input)
                    SessionMemory.append_ai(query.session_id, msg)
                return {"response": msg, "session_id": query.session_id}
    executor = build_agent(agent_name, extra_tools=query.extra_tools)

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
