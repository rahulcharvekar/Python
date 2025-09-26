from typing import Dict

from .base import AgentHandler
from .handlers.doc_help import DocHelpHandler
from .handlers.recruiter import RecruiterHandler


_HANDLERS: Dict[str, AgentHandler] = {
    "dochelp": DocHelpHandler(),
    "recruiter": RecruiterHandler(),
}


def get_handler(name: str) -> AgentHandler:
    # Default to DocHelp-style behavior if unknown
    return _HANDLERS.get(name, _HANDLERS["dochelp"])  # type: ignore[index]
