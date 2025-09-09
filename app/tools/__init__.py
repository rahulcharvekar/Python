from typing import List, Dict

# Import tool modules here. New tools can be added by creating a file
# in this package and importing it below.
from .chat_tools import chat_over_file
from .insight_tools import initialize_insights
from .registry_tools import list_files


# Central registry of all available tools for agents to use.
# To add a new tool, export it from a module and append it here.
ALL_TOOLS = [
    chat_over_file,
    initialize_insights,
    list_files,
]


def get_tools_by_names(names: List[str] | None = None):
    if not names:
        return ALL_TOOLS
    by_name: Dict[str, object] = {t.name: t for t in ALL_TOOLS}
    return [by_name[n] for n in names if n in by_name]

