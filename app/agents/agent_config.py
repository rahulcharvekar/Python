from typing import Dict, List


# Define agent configurations here. Each agent selects a subset of tools
# by name and can have a distinct system prompt. Add more agents as needed.
AGENTS: Dict[str, dict] = {
    "default": {
        "description": "General assistant over uploaded documents",
        "tools": [
            "list_files",
            "initialize_insights",
            "chat_over_file",
        ],
        "system_prompt": (
            "You are a helpful AI assistant for a document Q&A and indexing service. "
            "Choose tools to: list files, initialize vector indexes for a file, "
            "or answer questions using a specific file. Prefer using tools rather than guessing."
        ),
    },
    # Example of a specialized agent that only chats over files
    "chat_only": {
        "description": "Answers questions over a specified file",
        "tools": ["chat_over_file"],
        "system_prompt": (
            "You answer questions using the provided file only. "
            "Always call the chat_over_file tool with file and query."
        ),
    },
}

