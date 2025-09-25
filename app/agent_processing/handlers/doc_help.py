from typing import List
from ..base import AgentHandler, AgentContext, AgentResult
from ..common import run_agent, select_unique_files
import os
from app.services.generic import ingestion_db


def _get_known_files() -> List[str]:
    """Return files known for DocHelp from SQLite (ingestion_db)."""
    try:
        allowed = {".pdf", ".csv", ".txt", ".md", ".docx", ".doc"}
        rows = ingestion_db.list_documents("DocHelp")
        files = [r.get("file") for r in rows if isinstance(r, dict)]
        return [f for f in files if isinstance(f, str) and os.path.splitext(f)[1].lower() in allowed]
    except Exception:
        return []


class DocHelpHandler(AgentHandler):
    def handle(self, ctx: AgentContext) -> AgentResult:
        known_files = _get_known_files()
        # Minimal guard: avoid LLM call when no files available
        if not known_files:
            msg = (
                "This assistant answers questions grounded in uploaded files. "
                "Please upload a file and ask your question about it."
            )

            return AgentResult(response=msg, session_id=ctx.session_id, files=[])

        # Filename override via API payload: pin to session and use directly
        active_file = None
        selected_via_payload = False
        if ctx.file_override:
            if ctx.file_override in known_files:
                active_file = ctx.file_override
                selected_via_payload = True
            else:
                options = ", ".join(known_files[:10]) + (" …" if len(known_files) > 10 else "")
                msg = (
                    f"File not found: {ctx.file_override}. Please provide an exact filename." +
                    (f" Options: {options}" if options else "")
                )

                return AgentResult(response=msg, session_id=ctx.session_id, files=[])

        # Session-pinned file selection for DocHelp (fallback when no override)
        if not active_file:
            active_file = None

        # If user mentions a known filename explicitly, pin it
        lowered = (ctx.input_text or "").lower()
        mentioned = None
        for f in known_files:
            if f.lower() in lowered:
                mentioned = f
                break
        if mentioned:
            active_file = mentioned

        # Require explicit file selection before running the agent
        if not active_file:
            if len(known_files) == 1:
                active_file = known_files[0]
            else:
                options = ", ".join(known_files[:10]) + (" …" if len(known_files) > 10 else "")
                msg = (
                    "Please specify which uploaded file to use before continuing. "
                    + (f"Options: {options}" if options else "No files found in storage.")
                )

                return AgentResult(response=msg, session_id=ctx.session_id, files=[])

        # Run the selected agent (DocHelp or similarly configured)
        input_text = ctx.input_text
        if active_file:
            # Keep a soft hint in the input, and also pass explicit prompt vars
            input_text = f"Use file '{active_file}' for all tool calls in this session. " + (ctx.input_text or "")
        output = run_agent(
            agent_name=ctx.agent_name,
            input_text=input_text,
            extra_tools=ctx.extra_tools,
            session_id=ctx.session_id,
            prompt_vars={"doc_file": active_file} if active_file else None,
        )

        files = []
        if active_file and not selected_via_payload:
            files = select_unique_files([active_file])
        return AgentResult(response=output, session_id=ctx.session_id, files=files)
