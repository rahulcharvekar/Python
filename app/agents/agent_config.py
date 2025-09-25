from typing import Dict


# Define agent configurations here. Each agent selects a subset of tools
# by name and can have a distinct system prompt. Add more agents as needed.
#
# Prompt variables (handled by agent handlers via build_agent(prompt_vars=...)):
# - Common: {doc_file} — if set by the handler, indicates the selected/active file for this session.
#   Add new variables by referencing them in the agent's `system_prompt` and supplying them
#   from the corresponding handler.
AGENTS: Dict[str, dict] = {
    "dochelp": {
        "description": "General assistant over uploaded documents",
        "welcomemessage": "Welcome! I can help answer questions about your uploaded documents. Upload a file and ask away.",
        "commands": [],
        "keyword_search": "no",
        "examples": [
            "What are the key terms in invoice_0423.pdf?",
            "Summarize the main findings in report_q2.pdf",
            "Compare pricing across the uploaded CSV files"
        ],
        "capabilities": ["AI", "Upload Enabled", "PDF/CSV"],
        "tools": [
            "list_agent_files",
            "initialize_insights",
            "chat_over_file",
            "check_file_ready",
        ],
        "system_prompt": (
            "You are a helpful AI assistant for a document Q&A and indexing service. "
            "Orchestrate the best next action using the available tools.\n"
            "If a specific document has been selected for this session, it is provided as {doc_file}. When {doc_file} is set, restrict all tool calls to that file only. Do not switch files unless the user explicitly asks.\n"
            "- First call initialize_insights(file) with {doc_file} (or with the user-specified file if {doc_file} is not set). This call is idempotent; call it even if you are unsure whether indexing already exists.\n"
            "- After initialize_insights(file), immediately call chat_over_file(file, query) to answer using the file's content in the same turn.\n"
            "- If you need to verify whether a file is ready before answering, call check_file_ready(file) and report readiness concisely.\n"
            "- If the file name is missing or ambiguous and {doc_file} is not set, ask one brief clarifying question. You may call list_files() to show options.\n"
            "- If the question is general or not grounded in a file and {doc_file} is not set, ask the user which uploaded file to use. Do not answer without a file.\n"
            "Keep responses concise."
        ),
    },
}
