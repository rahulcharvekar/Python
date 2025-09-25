from typing import List, Optional, Sequence

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
    chat_history = []

    result = executor.invoke({"input": input_text, "chat_history": chat_history})
    return result.get("output", result)


def select_unique_files(file_names: Sequence[str]) -> List[str]:
    """Return unique filenames in order, skipping blanks and non-strings."""
    seen: set[str] = set()
    output: List[str] = []
    for name in file_names:
        if not isinstance(name, str):
            continue
        normalized = name.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output
