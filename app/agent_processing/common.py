from typing import Optional

from app.agents.agent_factory import build_agent


def run_agent(
    *,
    agent_name: str,
    input_text: str,
    extra_tools: Optional[list[str]] = None,
    session_id: Optional[str] = None,
    prompt_vars: Optional[dict] = None,
):
    executor = build_agent(agent_name, extra_tools=extra_tools, prompt_vars=prompt_vars)

    payload = {
        "input": input_text,
        "chat_history": [],
    }
    if session_id:
        payload["session_id"] = session_id

    result = executor.invoke(payload)
    return result.get("output", result)
