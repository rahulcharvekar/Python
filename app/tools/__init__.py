from typing import List, Dict

# Import tool modules here. New tools can be added by creating a file
# in this package and importing it below.
from .chat_tools import chat_over_file, chat_over_profile
from .insight_tools import initialize_insights
from .status_tools import check_file_ready
from .context_tools import build_context, normalize_query
from .reindex_tools import reindex_file
from .agent_file_tools import list_agent_files


# Central registry of all available tools for agents to use.
# To add a new tool, export it from a module and append it here.
ALL_TOOLS = [
    chat_over_file,
    chat_over_profile,
    initialize_insights,
    list_agent_files,
    check_file_ready,
    build_context,
    normalize_query,
    reindex_file,
]


def get_tools_by_names(names: List[str] | None = None):
    if not names:
        return ALL_TOOLS
    by_name: Dict[str, object] = {t.name: t for t in ALL_TOOLS}
    return [by_name[n] for n in names if n in by_name]
