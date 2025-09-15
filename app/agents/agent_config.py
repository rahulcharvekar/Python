from typing import Dict


# Define agent configurations here. Each agent selects a subset of tools
# by name and can have a distinct system prompt. Add more agents as needed.
#
# Prompt variables (handled by agent handlers via build_agent(prompt_vars=...)):
# - MyProfile: {profile_file} — injected by the MyProfile handler from settings.MYPROFILE_FILE.
#   Add new variables by referencing them in the agent's `system_prompt` and supplying them
#   from the corresponding handler.
AGENTS: Dict[str, dict] = {
    "DocHelp": {
        "description": "General assistant over uploaded documents",
        "welcomemessage": "Welcome! I can help answer questions about your uploaded documents. Upload a file and ask away.",
        "examples": [
            "What are the key terms in invoice_0423.pdf?",
            "Summarize the main findings in report_q2.pdf",
            "Compare pricing across the uploaded CSV files"
        ],
        "capabilities": ["file-qna", "indexing", "status-check"],
        "tools": [
            "list_files",
            "initialize_insights",
            "chat_over_file",
            "check_file_ready",
        ],
        # UI hint: this agent expects users to upload/select files
        "isuploadrequired": "yes",
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
    "MyProfile": {
        "description": "My Profile Q&A grounded in a single preconfigured resume/profile using tools",
        "welcomemessage": "Hi! I am Rahul Charvekar, you can interact with this AI assistant to know more about my profile.",
        "examples": [
            "Give me a short summary of Rahul's experience",
            "What cloud platforms has Rahul worked with?",
            "Write a 3-sentence pitch for a data engineer role"
        ],
        "capabilities": ["profile-qna", "concise-tone"],
        # Optional LLM overrides for this agent (uncomment or adjust as needed)
        # "llm": {
        #     "model": "gpt-4o-mini",
        #     "temperature": 0,
        #     # "base_url": "http://127.0.0.1:11434/v1",  # example custom endpoint
        # },
        "tools": [
            "initialize_insights",
            "normalize_query",
            "chat_over_profile",
            "check_file_ready",
        ],
        # UI hint: no upload is required for this agent (uses preconfigured profile)
        "isuploadrequired": "no",
        "system_prompt": (
            "You are acting as the candidate, speaking in first person (I, me, my) to a recruiter or in seconf person like person's name in {profile_file}.\n"
            "There is exactly one canonical resume/profile file: {profile_file}.\n"
            "Tone: professional, friendly, concise. Never disclose that you are an AI or mention tools/files.\n"
            "\n"
            "Tool policy:\n"
            "- Before answering, call initialize_insights(file) with {profile_file} (idempotent).\n"
            "- Normalize the user's input by calling normalize_query(query) and use that result as the query.\n"
            "- Then call chat_over_profile(file, query) with {profile_file} using the normalized query to generate the answer in the same turn.\n"
            "- Optionally call check_file_ready(file) with {profile_file} if needed.\n"
            "\n"
            "Answering rules:\n"
            "- Use only information from the profile and any user-provided facts in this chat. Do not speculate or fabricate.\n"
            "- If the requested information is not present, reply exactly: 'I am not able to find the exact match in profile, can you rephrase your query'\n"
            "- Prefer present tense and first person or second person phrasing, depending on the query referencing.\n"
            "- Keep responses succinct and recruiter-facing; when asked for a summary, provide 3–5 sentences or a short bullet list.\n"
        ),
    },
}
