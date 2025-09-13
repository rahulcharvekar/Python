from typing import List, Optional, Dict, Any

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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
    # Inject dynamic config into certain agent prompts (e.g., MyProfile)
    if agent_name == "MyProfile":
        try:
            system_prompt = system_prompt.format(profile_file=(settings.MYPROFILE_FILE or "<UNCONFIGURED>"))
        except Exception:
            # Fallback without formatting if anything goes wrong
            pass
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    llm = _create_llm()

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
            "tools": cfg.get("tools", []),
            # Pass UI hint as yes|no as requested
            "isuploadrequired": cfg.get("isuploadrequired", "yes"),
        }
    return out


def select_agent_name(user_input: str) -> str:
    """Select an agent name based on config-driven selection hints.

    Looks at each agent's optional `select` block in AGENTS to compute a score:
      - If `keywords_all` is present, all must be contained in the input.
      - `keywords_any` adds +1 per keyword match.
      - `priority` is added as a bias for tie-breaking.

    Falls back to "default" or the first configured agent when no match.
    """
    text = (user_input or "").lower()

    best_name: Optional[str] = None
    best_score: Optional[int] = None

    for name, cfg in AGENTS.items():
        sel = (cfg or {}).get("select") or {}
        kw_all = [str(k).lower() for k in sel.get("keywords_all", [])]
        kw_any = [str(k).lower() for k in sel.get("keywords_any", [])]
        priority = int(sel.get("priority", 0) or 0)

        # If keywords_all provided and not all present, skip this agent
        if kw_all and not all(k in text for k in kw_all):
            continue

        hits = sum(1 for k in kw_any if k in text) if kw_any else 0
        score = priority + hits

        # If agent has no select hints at all, treat as low priority candidate
        if not kw_all and not kw_any and priority == 0:
            # Only consider if we have no better match yet
            if best_score is None:
                best_name, best_score = name, -1
            continue

        if best_score is None or score > best_score:
            best_name, best_score = name, score

    if best_name:
        return best_name

    # Fallbacks
    return "default" if "default" in AGENTS else next(iter(AGENTS))
