from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Any, List


@dataclass
class AgentContext:
    input_text: str
    agent_name: str
    extra_tools: Optional[list[str]]
    session_id: Optional[str]
    # Optional per-request file selection that overrides session selection
    file_override: Optional[str] = None


@dataclass
class AgentResult:
    response: Any
    session_id: Optional[str]
    files: Optional[List[str]] = None


class AgentHandler(Protocol):
    def handle(self, ctx: AgentContext) -> AgentResult:  # pragma: no cover - interface
        ...
