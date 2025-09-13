from typing import Optional, Dict, Any
from .registry import get_handler
from .base import AgentContext


def handle_agent_query(
    *,
    input_text: str,
    agent: Optional[str] = None,
    extra_tools: Optional[list[str]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Entry point for processing an agent query. Selects the agent, builds context,
    delegates to the appropriate handler, and returns a response dict.
    """
    ctx = AgentContext(
        input_text=input_text,
        agent_name=agent,
        extra_tools=extra_tools,
        session_id=session_id,
    )

    handler = get_handler(agent)
    result = handler.handle(ctx)
    return {"response": result.response, "session_id": result.session_id}
