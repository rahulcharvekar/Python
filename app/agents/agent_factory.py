from typing import List, Optional, Dict, Any

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.tools import get_tools_by_names
from .agent_config import AGENTS


def _create_llm():
    """Create a ChatOpenAI-compatible LLM using environment settings."""
    app_env = (settings.APP_ENV or "").lower()
    if app_env == "development":
        # Use local OpenAI-compatible server (e.g., Ollama) if configured
        return ChatOpenAI(
            model=settings.LOCAL_LLM_MODEL,
            base_url=settings.LOCAL_LLM_BASE_URL,
            api_key=settings.LOCAL_LLM_API_KEY,
            temperature=0,
        )
    # Production: OpenAI hosted
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )


def build_agent(agent_name: str = "default", *, extra_tools: Optional[List[str]] = None) -> AgentExecutor:
    """
    Build an AgentExecutor using the named agent configuration and optional extra tools.
    """
    cfg = AGENTS.get(agent_name)
    if not cfg:
        raise ValueError(f"Unknown agent: {agent_name}")

    tool_names = list(cfg.get("tools", []))
    if extra_tools:
        # Allow callers to extend the toolset on the fly
        tool_names.extend([t for t in (extra_tools or []) if t not in tool_names])

    tools = get_tools_by_names(tool_names)

    system_prompt = cfg.get("system_prompt") or "You are a helpful assistant."
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    llm = _create_llm()

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
    return executor


def list_agents() -> Dict[str, Any]:
    """Return available agent names and basic descriptions."""
    return {name: {"description": cfg.get("description"), "tools": cfg.get("tools", [])} for name, cfg in AGENTS.items()}

