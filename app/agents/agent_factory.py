from typing import List, Optional, Dict, Any
import string

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.core.config import settings
from app.tools import get_tools_by_names
from .agent_config import AGENTS
from app.utils.Logging.logger import logger


def _create_llm(overrides: Optional[Dict[str, Any]] = None):
    """Create a ChatOpenAI-compatible LLM using environment settings or overrides."""
    if overrides:
        try:
            return ChatOpenAI(
                model=overrides.get("model", settings.OPENAI_MODEL),
                api_key=overrides.get("api_key", settings.OPENAI_API_KEY),
                base_url=overrides.get("base_url"),
                temperature=overrides.get("temperature", 0),
            )
        except Exception as e:
            logger.error(f"LLM override creation failed, falling back to defaults: {e}")

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


def _render_prompt(template: str, prompt_vars: Optional[Dict[str, Any]]) -> str:
    """Safely render a prompt; log missing placeholders and fall back on errors."""
    if not prompt_vars:
        return template
    try:
        fields = {fname for _, fname, _, _ in string.Formatter().parse(template) if fname}
        missing = [f for f in fields if f not in (prompt_vars or {})]
        if missing:
            logger.warning(f"Prompt variables missing for placeholders: {missing}")
        return template.format(**prompt_vars)
    except Exception as e:
        logger.error(f"Prompt render failed; using template as-is. Error: {e}")
        return template


def build_agent(
    agent_name,
    *,
    extra_tools: Optional[List[str]] = None,
    prompt_vars: Optional[Dict[str, Any]] = None,
) -> AgentExecutor:
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
    # Allow handlers to inject dynamic variables into the prompt in a generic way
    system_prompt = _render_prompt(system_prompt, prompt_vars)
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    llm_overrides = cfg.get("llm") if isinstance(cfg.get("llm"), dict) else None
    llm = _create_llm(llm_overrides)

    agent = create_tool_calling_agent(llm, tools, prompt)
    # Add a safety cap to avoid runaway tool loops
    executor = AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=6)
    return executor


def list_agents() -> Dict[str, Any]:
    """Return available agent names and metadata for UI rendering."""
    out: Dict[str, Any] = {}
    for name, cfg in AGENTS.items():
        out[name] = {
            "description": cfg.get("description"),
            "welcomemessage": cfg.get("welcomemessage"),
            "commands": cfg.get("commands", []),
            "tools": cfg.get("tools", []),
            # Pass UI hint as yes|no as requested
            "isuploadrequired": cfg.get("isuploadrequired", "yes"),
            "examples": cfg.get("examples", []),
            "capabilities": cfg.get("capabilities", []),
            # surface model hint if configured
            "model": (cfg.get("llm") or {}).get("model") if isinstance(cfg.get("llm"), dict) else None,
        }
    return out
