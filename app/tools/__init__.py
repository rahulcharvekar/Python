from typing import List, Dict

# Import tool modules here. New tools can be added by creating a file
# in this package and importing it below.
from .generic import (
    initialize_insights,
    check_file_ready,
    build_context,
    normalize_query,
    reindex_file,
    list_agent_files,
    extract_keywords,
)
from .agent.dochelp_tools import chat_over_file, list_indexed_docs_db
from .agent.recruiter_tools import enrich_resume, list_indexed_profiles_db, chat_over_profile


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
    extract_keywords,
    enrich_resume,
    list_indexed_profiles_db,
    list_indexed_docs_db,
]


def get_tools_by_names(names: List[str] | None = None):
    if not names:
        return ALL_TOOLS
    by_name: Dict[str, object] = {t.name: t for t in ALL_TOOLS}
    return [by_name[n] for n in names if n in by_name]
