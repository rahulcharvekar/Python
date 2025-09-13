from typing import Dict

from .base import AgentHandler
from .handlers.doc_help import DocHelpHandler
from .handlers.my_profile import MyProfileHandler


_HANDLERS: Dict[str, AgentHandler] = {
    "DocHelp": DocHelpHandler(),
    "MyProfile": MyProfileHandler(),
}


def get_handler(name: str) -> AgentHandler:
    # Default to DocHelp-style behavior if unknown
    return _HANDLERS.get(name, _HANDLERS["DocHelp"])  # type: ignore[index]

