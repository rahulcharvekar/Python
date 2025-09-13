from typing import List, Optional, Any

from app.agents.agent_factory import build_agent
from app.agents.session_memory import SessionMemory


def session_append_user(session_id: Optional[str], text: str) -> None:
    if session_id:
        SessionMemory.append_user(session_id, text)


def session_append_ai(session_id: Optional[str], text: str) -> None:
    if session_id and isinstance(text, str):
        SessionMemory.append_ai(session_id, text)


def session_get_history(session_id: Optional[str]) -> List[Any]:
    if session_id:
        return SessionMemory.get(session_id)
    return []


def run_agent(
    *,
    agent_name: str,
    input_text: str,
    extra_tools: Optional[list[str]] = None,
    session_id: Optional[str] = None,
    prompt_vars: Optional[dict] = None,
):
    executor = build_agent(agent_name, extra_tools=extra_tools, prompt_vars=prompt_vars)
    chat_history = []
    if session_id:
        session_append_user(session_id, input_text)
        chat_history = session_get_history(session_id)

    result = executor.invoke({"input": input_text, "chat_history": chat_history})
    return result.get("output", result)
