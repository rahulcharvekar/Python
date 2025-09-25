from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Any, List


@dataclass
class AgentContext:
    input_text: str
    agent_name: str
    filename: Optional[str] = None
    extra_tools: Optional[list[str]] = None
    session_id: Optional[str] = None


@dataclass
class AgentResult:
    response: Any
    session_id: Optional[str]
    files: Optional[List[str]] = None


class AgentHandler(Protocol):
    def handle(self, ctx: AgentContext) -> AgentResult:  # pragma: no cover - interface
        ...
