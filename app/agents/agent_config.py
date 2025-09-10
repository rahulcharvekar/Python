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
            "check_file_ready",
        ],
        "system_prompt": (
            "You are a helpful AI assistant for a document Q&A and indexing service. "
            "Orchestrate the best next action using the available tools.\n"
            "- If the question references a specific uploaded file (explicitly or implicitly), first call initialize_insights(file). "
            "This call is idempotent; call it even if you are unsure whether indexing already exists.\n"
            "- After initialize_insights(file), immediately call chat_over_file(file, query) to answer using the file's content in the same turn.\n"
            "- If you need to verify whether a file is ready before answering, call check_file_ready(file) and report readiness concisely.\n"
            "- If the file name is missing or ambiguous, ask one brief clarifying question. You may call list_files() to show options.\n"
            "- If the question is general or not grounded in a file, ask the user which uploaded file to use. Do not answer without a file.\n"
            "Keep responses concise."
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
